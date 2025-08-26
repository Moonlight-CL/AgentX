#!/usr/bin/env python3
"""
todo：
1. diff 成本，并且将 diff 后值显示在 primary 节点
2. 再次看下 gp3，io1 的iops 以及 throughput 的单价

RDS MySQL和Aurora MySQL定价分析工具 - TAZ支持版本（r7g/r8g专版）
支持获取指定区域的RDS MySQL实例信息，并计算RDS和Aurora的RI定价
Aurora转换支持r7g、r8g两种实例类型，分别计算实例成本、存储成本和总MRR成本
RDS替换支持r7g、r8g两种实例类型，分别计算实例成本、存储成本和总MRR成本
新增存储信息获取功能：磁盘类型、容量、IOPS、带宽、使用量和存储成本计算

新增TAZ（三可用区数据库集群部署）支持：
1. 通过DBClusterIdentifier识别Aurora集群
2. 通过describe-db-clusters API识别Primary节点
3. 在Aurora转换成本计算时，将存储成本分配到Primary节点
4. 支持单实例、MAZ和TAZ三种架构的处理
5. 分别计算Aurora实例MRR、存储MRR和总MRR成本

新增RDS替换机型成本计算：
1. 支持r7g、r8g两种RDS替换实例类型
2. 计算RDS替换实例MRR、存储MRR和总MRR成本
3. Multi-AZ架构下，实例和存储单价及MRR都乘以2
4. 保持现有Aurora转换逻辑不变

Multi-AZ存储成本优化：
1. 当RDS MySQL是Multi-AZ架构时，迁移到Aurora时，存储成本不乘以2，仅算一份
2. 当Multi-AZ架构并且有多个read replica时，迁移到Aurora的存储成本计算到Primary节点上，仅计算一份
3. RDS替换场景下，Multi-AZ存储成本仍然乘以2（保持RDS原有逻辑）

RDS MySQL集群支持：
1. 通过source_db_instance_identifier识别RDS MySQL集群关系
2. 当read replica的source_db_instance_identifier值和primary的db_instance_identifier值相同时，识别为集群
3. 迁移到Aurora时，集群的存储成本仅计算一次，并加和到Primary节点上
4. Read replica节点的Aurora存储成本为0，避免重复计算
5. 支持复杂的集群拓扑，包括一个primary对应多个read replica的场景

Aurora存储容量优化：
1. aurora_allocate_storage_gb 基于 Primary节点的 used_storage_gb（实际使用量）计算
2. 符合Aurora共享存储特性，不累加集群中所有节点的存储量
3. 更准确反映迁移到Aurora后的实际存储需求和成本
4. 优先使用Primary节点的实际使用量，如果未获取到则回退到分配量
5. 避免基于过度分配或重复计算的存储容量进行成本计算
"""

import argparse
import csv
import json
import logging
import sys
import time
from typing import Dict, List, Optional, Tuple
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class RDSAuroraMultiGenerationPricingAnalyzer:
    def __init__(self, region: str):
        """
        初始化分析器
        
        Args:
            region: AWS区域名称
        """
        self.region = region
        self.rds_client = boto3.client('rds', region_name=region)
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')  # Pricing API只在us-east-1可用
        self.sts_client = boto3.client('sts', region_name=region)
        self.cloudwatch_client = boto3.client('cloudwatch', region_name=region)
        
        # 缓存定价信息
        self.rds_pricing_cache = {}
        self.aurora_pricing_cache = {}  # 缓存所有Aurora实例类型的定价
        self.pricing_cache = {}  # 存储所有实例的定价信息
        self.storage_pricing_cache = {}  # 存储定价缓存
        self.aurora_storage_pricing_cache = {}  # Aurora存储定价缓存
        
        # Aurora实例类型列表 - 只保留r7g和r8g
        self.aurora_generations = ['r7g', 'r8g']
        
        # RDS替换实例类型列表 - r7g和r8g
        self.rds_replacement_generations = ['r7g', 'r8g']
        
        # 集群信息缓存
        self.aurora_clusters_cache = {}
        
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def get_all_aurora_clusters(self) -> Dict[str, Dict]:
        """
        获取所有Aurora集群信息并缓存
        
        Returns:
            集群信息字典，key为集群ID，value为集群详细信息
        """
        if self.aurora_clusters_cache:
            self.logger.info("Aurora集群缓存已存在，跳过重复获取")
            return self.aurora_clusters_cache
        
        try:
            self.logger.info("开始获取Aurora集群信息...")
            paginator = self.rds_client.get_paginator('describe_db_clusters')
            
            for page in paginator.paginate():
                for cluster in page['DBClusters']:
                    # 只处理MySQL引擎的集群
                    if cluster.get('Engine') in ['aurora-mysql', 'mysql']:
                        cluster_id = cluster['DBClusterIdentifier']
                        
                        # 识别Primary节点
                        primary_node = self._identify_cluster_primary_node(cluster)
                        
                        # 构建集群信息
                        cluster_info = {
                            'cluster_id': cluster_id,
                            'engine': cluster.get('Engine'),
                            'engine_version': cluster.get('EngineVersion'),
                            'primary_node': primary_node,
                            'members': cluster.get('DBClusterMembers', []),
                            'multi_az': cluster.get('MultiAZ', False),
                            'endpoint': cluster.get('Endpoint'),
                            'reader_endpoint': cluster.get('ReaderEndpoint')
                        }
                        
                        self.aurora_clusters_cache[cluster_id] = cluster_info
                        
                        self.logger.info(f"找到Aurora集群: {cluster_id}, Primary节点: {primary_node}, "
                                       f"成员数: {len(cluster_info['members'])}")
            
            self.logger.info(f"共缓存 {len(self.aurora_clusters_cache)} 个Aurora MySQL集群")
            return self.aurora_clusters_cache
            
        except Exception as e:
            self.logger.error(f"获取Aurora集群失败: {e}")
            return {}

    def _identify_cluster_primary_node(self, cluster_info: Dict) -> Optional[str]:
        """
        识别Aurora集群的Primary节点
        
        Args:
            cluster_info: 集群信息字典
            
        Returns:
            Primary节点的实例标识符，如果未找到返回None
        """
        try:
            cluster_members = cluster_info.get('DBClusterMembers', [])
            
            for member in cluster_members:
                if member.get('IsClusterWriter', False):
                    primary_instance = member['DBInstanceIdentifier']
                    return primary_instance
            
            self.logger.warning(f"集群 {cluster_info.get('DBClusterIdentifier')} 未找到Primary节点")
            return None
            
        except Exception as e:
            self.logger.error(f"识别Primary节点失败: {e}")
            return None

    def get_storage_info(self, db_instance_identifier: str, db_instance_data: Dict) -> Dict:
        """
        获取RDS实例的存储信息
        
        Args:
            db_instance_identifier: 数据库实例标识符
            db_instance_data: 数据库实例的详细信息
            
        Returns:
            包含存储信息的字典
        """
        storage_info = {
            'storage_type': 'unknown',
            'allocated_storage_gb': 0,
            'max_allocated_storage_gb': 0,
            'iops': 0,
            'storage_throughput_mbps': 0,
            'storage_encrypted': False
        }
        
        try:
            # 从实例信息中获取存储配置
            storage_info['storage_type'] = db_instance_data.get('StorageType', 'unknown')
            storage_info['allocated_storage_gb'] = db_instance_data.get('AllocatedStorage', 0)
            storage_info['max_allocated_storage_gb'] = db_instance_data.get('MaxAllocatedStorage', 0)
            storage_info['iops'] = db_instance_data.get('Iops', 0)
            storage_info['storage_throughput_mbps'] = db_instance_data.get('StorageThroughput', 0)
            storage_info['storage_encrypted'] = db_instance_data.get('StorageEncrypted', False)
            
            # 获取已使用的存储空间（通过CloudWatch指标）
            free_storage = self._get_used_storage_from_cloudwatch(db_instance_identifier)
            storage_info['free_storage_gb'] = free_storage
            
            self.logger.info(f"实例 {db_instance_identifier} 存储信息: "
                           f"类型={storage_info['storage_type']}, "
                           f"分配={storage_info['allocated_storage_gb']}GB, "
                           f"剩余={storage_info['free_storage_gb']}GB, "
                           f"IOPS={storage_info['iops']}, "
                           f"吞吐量={storage_info['storage_throughput_mbps']}MB/s")
            
        except Exception as e:
            self.logger.error(f"获取实例 {db_instance_identifier} 存储信息失败: {e}")

        return storage_info

    def _get_used_storage_from_cloudwatch(self, db_instance_identifier: str) -> float:
        """
        从CloudWatch获取数据库实例的剩余的存储空间
        
        Args:
            db_instance_identifier: 数据库实例标识符
            
        Returns:
            剩余的存储空间（GB），如果获取失败返回'unknown'
        """
        try:
            # 获取过去24小时的平均已使用存储空间
            response = self.cloudwatch_client.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName='DatabaseConnections',  # 先尝试获取连接数来验证实例存在
                Dimensions=[
                    {
                        'Name': 'DBInstanceIdentifier',
                        'Value': db_instance_identifier
                    }
                ],
                StartTime=time.time() - 86400,  # 24小时前
                EndTime=time.time(),
                Period=3600,  # 1小时间隔
                Statistics=['Average']
            )
            
            # 如果能获取到连接数指标，说明实例存在，尝试获取存储使用量
            if response['Datapoints']:
                # 获取FreeStorageSpace指标
                storage_response = self.cloudwatch_client.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='FreeStorageSpace',
                    Dimensions=[
                        {
                            'Name': 'DBInstanceIdentifier',
                            'Value': db_instance_identifier
                        }
                    ],
                    StartTime=time.time() - 86400,
                    EndTime=time.time(),
                    Period=3600,
                    Statistics=['Average']
                )
                
                if storage_response['Datapoints']:
                    # 获取最新的空闲存储空间（字节）
                    latest_datapoint = max(storage_response['Datapoints'], key=lambda x: x['Timestamp'])
                    free_storage_bytes = latest_datapoint['Average']
                    free_storage_gb = free_storage_bytes / (1024 ** 3)  # 转换为GB
                    
                    return free_storage_gb
            
            return 'unknown'
            
        except Exception as e:
            self.logger.warning(f"从CloudWatch获取实例 {db_instance_identifier} 存储使用量失败: {e}")
            return 'unknown'

    def get_all_storage_pricing(self) -> None:
        """
        一次性获取该region下RDS MySQL Single-AZ的所有磁盘类型的存储单价、IOPS单价以及bandwidth单价，并进行缓存
        减少API调用次数，提高效率
        """
        if self.storage_pricing_cache:
            self.logger.info("存储定价缓存已存在，跳过重复获取")
            return
        
        self.logger.info(f"开始获取区域 {self.region} 的所有存储类型定价...")
        
        # 支持的存储类型映射
        storage_type_mapping = {
            'General Purpose': 'gp2',
            'General Purpose-GP3': 'gp3', 
            'Provisioned IOPS': 'io1',
            'Provisioned IOPS-IO2': 'io2',
            'Magnetic': 'magnetic'
        }
        
        try:
            # 构建基础过滤器 - 获取所有RDS MySQL存储定价
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Database Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'}
            ]
            
            # 使用分页获取所有存储产品
            paginator = self.pricing_client.get_paginator('get_products')
            page_iterator = paginator.paginate(
                ServiceCode='AmazonRDS',
                Filters=filters
            )
            
            # 初始化所有存储类型的定价信息
            for storage_type in storage_type_mapping.values():
                self.storage_pricing_cache[storage_type] = {
                    'storage_price_per_gb_month': 0,
                    'iops_price_per_iops_month': 0,
                    'throughput_price_per_mbps_month': 0
                }
            
            processed_count = 0
            for page in page_iterator:
                for price_item in page['PriceList']:
                    product = json.loads(price_item)
                    attributes = product.get('product', {}).get('attributes', {})
                    
                    # 获取存储类型
                    volume_type = attributes.get('volumeType')
                    if not volume_type or volume_type not in storage_type_mapping:
                        continue
                    
                    storage_type = storage_type_mapping[volume_type]
                    
                    # 获取按需定价
                    terms = product.get('terms', {})
                    on_demand_terms = terms.get('OnDemand', {})
                    
                    for term_key, term_data in on_demand_terms.items():
                        price_dimensions = term_data.get('priceDimensions', {})
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            unit = price_data.get('unit', '')
                            
                            if usd_price and float(usd_price) > 0:
                                price_value = float(usd_price)
                                
                                # 根据单位确定价格类型
                                if 'GB-Mo' in unit:
                                    self.storage_pricing_cache[storage_type]['storage_price_per_gb_month'] = price_value
                                elif 'IOPS-Mo' in unit:
                                    self.storage_pricing_cache[storage_type]['iops_price_per_iops_month'] = price_value
                                elif 'MBps-Mo' in unit or 'MB/s-Mo' in unit:
                                    self.storage_pricing_cache[storage_type]['throughput_price_per_mbps_month'] = price_value
                                
                                processed_count += 1
            
            # 获取io1和io2的IOPS定价（使用专门的方法）
            self._get_iops_pricing_for_provisioned_storage()
            
            # 记录缓存结果
            for storage_type, pricing_info in self.storage_pricing_cache.items():
                if any(pricing_info.values()):  # 只记录有定价信息的存储类型
                    self.logger.info(f"存储类型 {storage_type} 定价: "
                                   f"存储=${pricing_info['storage_price_per_gb_month']}/GB/月, "
                                   f"IOPS=${pricing_info['iops_price_per_iops_month']}/IOPS/月, "
                                   f"吞吐量=${pricing_info['throughput_price_per_mbps_month']}/MB/s/月")
            
            self.logger.info(f"存储定价缓存完成，共处理 {processed_count} 个定价项")
            
        except Exception as e:
            self.logger.error(f"获取存储定价失败: {e}")

    def _get_iops_pricing_for_provisioned_storage(self) -> None:
        """
        专门获取io1和io2存储类型的IOPS定价
        使用Provisioned IOPS产品族来获取IOPS定价
        """
        self.logger.info("开始获取io1和io2的IOPS定价...")
        
        # IOPS类型映射
        iops_type_mapping = {
            'io1': 'Provisioned IOPS',
            'io2': 'Provisioned IOPS-IO2'
        }
        
        for storage_type, volume_type in iops_type_mapping.items():
            try:
                # 构建IOPS定价查询过滤器
                filters = [
                    {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Provisioned IOPS'},
                    {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'},
                    {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()},
                    {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': volume_type}
                ]
                
                response = self.pricing_client.get_products(
                    ServiceCode='AmazonRDS',
                    Filters=filters,
                    FormatVersion='aws_v1',
                    MaxResults=100
                )
                
                # 解析IOPS定价
                for price_item in response['PriceList']:
                    product = json.loads(price_item)
                    
                    # 获取按需定价
                    terms = product.get('terms', {})
                    on_demand_terms = terms.get('OnDemand', {})
                    
                    for term_key, term_data in on_demand_terms.items():
                        price_dimensions = term_data.get('priceDimensions', {})
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            unit = price_data.get('unit', '')
                            
                            if usd_price and float(usd_price) > 0 and 'IOPS-Mo' in unit:
                                price_value = float(usd_price)
                                
                                # 确保存储类型已初始化
                                if storage_type not in self.storage_pricing_cache:
                                    self.storage_pricing_cache[storage_type] = {
                                        'storage_price_per_gb_month': 0,
                                        'iops_price_per_iops_month': 0,
                                        'throughput_price_per_mbps_month': 0
                                    }
                                
                                self.storage_pricing_cache[storage_type]['iops_price_per_iops_month'] = price_value
                                self.logger.info(f"获取到 {storage_type} IOPS定价: ${price_value}/IOPS/月")
                                break
                        else:
                            continue
                        break
                
            except Exception as e:
                self.logger.error(f"获取 {storage_type} IOPS定价失败: {e}")

    def get_storage_pricing(self, storage_type: str) -> Dict:
        """
        从缓存中获取存储类型的定价信息
        
        Args:
            storage_type: 存储类型 (gp2, gp3, io1, io2, magnetic)
            
        Returns:
            包含存储定价信息的字典
        """
        if not self.storage_pricing_cache:
            self.logger.warning("存储定价缓存为空，请先调用get_all_storage_pricing()方法")
            return {
                'storage_price_per_gb_month': 0,
                'iops_price_per_iops_month': 0,
                'throughput_price_per_mbps_month': 0
            }
        
        pricing_info = self.storage_pricing_cache.get(storage_type, {
            'storage_price_per_gb_month': 0,
            'iops_price_per_iops_month': 0,
            'throughput_price_per_mbps_month': 0
        })
        
        self.logger.debug(f"从缓存获取存储类型 {storage_type} 定价: {pricing_info}")
        return pricing_info

    def get_aurora_storage_pricing(self) -> Dict:
        """
        一次性获取某个region下Aurora存储的单价并缓存
        
        Returns:
            包含Aurora存储定价信息的字典
        """
        if self.aurora_storage_pricing_cache:
            self.logger.info("Aurora存储定价缓存已存在，跳过重复获取")
            return self.aurora_storage_pricing_cache
        
        self.logger.info(f"开始获取区域 {self.region} 的Aurora存储定价...")
        
        pricing_info = {
            'storage_price_per_gb_month': 0,
            'io_request_price_per_million': 0
        }
        
        try:
            # 构建Aurora存储定价查询过滤器
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Database Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'Aurora MySQL'}
            ]
            
            # 使用分页获取所有Aurora存储产品
            paginator = self.pricing_client.get_paginator('get_products')
            page_iterator = paginator.paginate(
                ServiceCode='AmazonRDS',
                Filters=filters
            )
            
            processed_count = 0
            for page in page_iterator:
                for price_item in page['PriceList']:
                    product = json.loads(price_item)
                    attributes = product.get('product', {}).get('attributes', {})
                    
                    # 获取按需定价
                    terms = product.get('terms', {})
                    on_demand_terms = terms.get('OnDemand', {})
                    
                    for term_key, term_data in on_demand_terms.items():
                        price_dimensions = term_data.get('priceDimensions', {})
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            unit = price_data.get('unit', '')
                            description = price_data.get('description', '')
                            
                            if usd_price and float(usd_price) > 0:
                                price_value = float(usd_price)
                                processed_count += 1
                                
                                # 根据单位和描述确定价格类型
                                if 'GB-Mo' in unit and 'storage' in description.lower():
                                    pricing_info['storage_price_per_gb_month'] = price_value
                                    self.logger.info(f"Aurora存储单价: ${price_value}/GB/月")
                                elif 'million' in unit.lower() and ('io' in description.lower() or 'request' in description.lower()):
                                    pricing_info['io_request_price_per_million'] = price_value
                                    self.logger.info(f"Aurora IO请求单价: ${price_value}/百万次请求")
            
            self.aurora_storage_pricing_cache = pricing_info
            self.logger.info(f"Aurora存储定价缓存完成，共处理 {processed_count} 个定价项")
            
        except Exception as e:
            self.logger.error(f"获取Aurora存储定价失败: {e}")
        
        return pricing_info
    def calculate_storage_cost(self, storage_info: Dict, storage_pricing: Dict, is_multi_az: bool = False, is_aurora_migration: bool = False) -> Dict:
        """
        计算存储总成本，包含GP3的baseline超出部分计费
        
        Args:
            storage_info: 存储信息字典
            storage_pricing: 存储定价信息字典
            is_multi_az: 是否为Multi-AZ架构
            is_aurora_migration: 是否为Aurora迁移场景
            
        Returns:
            包含存储成本信息的字典
        """
        cost_info = {
            'storage_cost_per_month': 0,
            'iops_cost_per_month': 0,
            'throughput_cost_per_month': 0,
            'total_storage_cost_per_month': 0,
            'gp3_baseline_exceeded_iops': 0,
            'gp3_baseline_exceeded_throughput': 0
        }
        
        try:
            # 计算存储成本
            allocated_storage = storage_info.get('allocated_storage_gb', 0)
            storage_price = storage_pricing.get('storage_price_per_gb_month', 0)
            cost_info['storage_cost_per_month'] = allocated_storage * storage_price
            
            # 获取IOPS和吞吐量信息
            iops = storage_info.get('iops', 0)
            throughput = storage_info.get('storage_throughput_mbps', 0)
            iops_price = storage_pricing.get('iops_price_per_iops_month', 0)
            throughput_price = storage_pricing.get('throughput_price_per_mbps_month', 0)
            
            # 判断存储类型，获取storage_type
            storage_type = storage_info.get('storage_type', 'unknown')
            
            # GP3存储类型的特殊处理
            if storage_type == 'gp3':
                # GP3 baseline: 12000 IOPS, 500 MB/s
                gp3_baseline_iops = 12000
                gp3_baseline_throughput = 500
                
                # 计算超出baseline的IOPS
                if iops > gp3_baseline_iops:
                    exceeded_iops = iops - gp3_baseline_iops
                    cost_info['gp3_baseline_exceeded_iops'] = exceeded_iops
                    cost_info['iops_cost_per_month'] = exceeded_iops * iops_price
                    self.logger.info(f"GP3 IOPS超出baseline: {exceeded_iops} IOPS，额外费用: ${cost_info['iops_cost_per_month']}/月")
                
                # 计算超出baseline的吞吐量
                if throughput > gp3_baseline_throughput:
                    exceeded_throughput = throughput - gp3_baseline_throughput
                    cost_info['gp3_baseline_exceeded_throughput'] = exceeded_throughput
                    cost_info['throughput_cost_per_month'] = exceeded_throughput * throughput_price
                    self.logger.info(f"GP3 吞吐量超出baseline: {exceeded_throughput} MB/s，额外费用: ${cost_info['throughput_cost_per_month']}/月")
                
            else:
                # 非GP3存储类型的IOPS和吞吐量计费（io1, io2等）
                if iops > 0 and iops_price > 0:
                    cost_info['iops_cost_per_month'] = iops * iops_price
                
                if throughput > 0 and throughput_price > 0:
                    cost_info['throughput_cost_per_month'] = throughput * throughput_price
            
            # 计算总成本
            total_cost = (cost_info['storage_cost_per_month'] + 
                         cost_info['iops_cost_per_month'] + 
                         cost_info['throughput_cost_per_month'])
            
            # Multi-AZ架构存储成本处理逻辑
            if is_multi_az and not is_aurora_migration:
                # 仅在非Aurora迁移场景下，Multi-AZ架构需要乘以2
                total_cost *= 2
                cost_info['storage_cost_per_month'] *= 2
                cost_info['iops_cost_per_month'] *= 2
                cost_info['throughput_cost_per_month'] *= 2
                self.logger.info("Multi-AZ架构，RDS存储成本乘以2")
            elif is_multi_az and is_aurora_migration:
                # Aurora迁移场景下，Multi-AZ存储成本不乘以2，仅计算一份
                self.logger.info("Multi-AZ架构迁移到Aurora，存储成本仅计算一份，不乘以2")
            
            cost_info['total_storage_cost_per_month'] = round(total_cost, 2)
            
        except Exception as e:
            self.logger.error(f"计算存储成本失败: {e}")
        
        return cost_info

    def get_account_id(self) -> str:
        """获取当前AWS账户ID"""
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            self.logger.error(f"获取账户ID失败: {e}")
            return "unknown"

    def get_all_rds_mysql_instances(self) -> List[Dict]:
        """
        获取指定区域下所有RDS MySQL实例的基本信息和存储信息
        仅处理db.m和db.r开头的实例类型，跳过db.t开头的实例
        支持TAZ架构识别
        
        Returns:
            包含实例信息和存储信息的字典列表
        """
        instances = []
        account_id = self.get_account_id()
        skipped_instances = []
        
        # 首先获取Aurora集群信息
        aurora_clusters = self.get_all_aurora_clusters()
        
        try:
            paginator = self.rds_client.get_paginator('describe_db_instances')
            all_db_instances = []
            
            # 首先获取所有实例信息
            for page in paginator.paginate():
                for db_instance in page['DBInstances']:
                    if db_instance.get('Engine') == 'mysql':
                        all_db_instances.append(db_instance)

            # 然后处理每个实例
            for db_instance in all_db_instances:
                instance_class = db_instance['DBInstanceClass']
                
                # 过滤实例类型：仅处理db.m和db.r开头的实例
                if self._should_process_instance(instance_class):
                    # 确定架构类型（支持TAZ）
                    architecture = self._determine_architecture_with_taz(db_instance, all_db_instances, aurora_clusters)
                    
                    # 获取存储信息
                    storage_info = self.get_storage_info(db_instance['DBInstanceIdentifier'], db_instance)
                    
                    # 计算已使用存储（如果获取到了空闲存储）
                    if isinstance(storage_info['free_storage_gb'], float):
                        allocated_storage = storage_info['allocated_storage_gb']
                        free_storage = storage_info['free_storage_gb']
                        storage_info['used_storage_gb'] = max(0, allocated_storage - free_storage)
                    
                    # 获取集群信息（如果是Aurora集群成员）
                    cluster_info = self._get_cluster_info(db_instance, aurora_clusters)
                    
                    # 处理source_db_instance_identifier字段
                    source_db_identifier = db_instance.get('ReadReplicaSourceDBInstanceIdentifier', 'N/A')
                    
                    # 特殊处理TAZ架构下的read replica
                    if architecture == 'taz_cluster' and not cluster_info.get('is_primary', True):
                        # TAZ架构下的read replica，显示writer node的实际db_instance_identifier
                        primary_node_id = cluster_info.get('primary_node_id')
                        if primary_node_id:
                            source_db_identifier = primary_node_id
                            self.logger.info(f"TAZ集群Reader节点 {db_instance['DBInstanceIdentifier']} 的source_db_instance_identifier设置为Primary节点: {primary_node_id}")
                        else:
                            source_db_identifier = 'writer-node'
                            self.logger.info(f"TAZ集群Reader节点 {db_instance['DBInstanceIdentifier']} 未找到Primary节点，使用默认值'writer-node'")
                    elif architecture == 'read_replica':
                        # 普通read replica，设置为"writer-node"
                        source_db_identifier = 'writer-node'
                        self.logger.info(f"Read replica实例 {db_instance['DBInstanceIdentifier']} 的source_db_instance_identifier设置为'writer-node'")
                    
                    instance_info = {
                        'db_instance_identifier': db_instance['DBInstanceIdentifier'],
                        'account_id': account_id,
                        'region': self.region,
                        'mysql_engine_version': db_instance.get('EngineVersion', 'unknown'),
                        'architecture': architecture,
                        'instance_class': instance_class,
                        'source_db_instance_identifier': source_db_identifier,
                        'multi_az': db_instance.get('MultiAZ', False),
                        'needs_aurora_conversion': True,  # 所有实例都需要Aurora转换测算
                        
                        # 集群相关信息
                        'cluster_identifier': cluster_info.get('cluster_id', 'N/A'),
                        'is_cluster_primary': cluster_info.get('is_primary', True),
                        'cluster_role': cluster_info.get('role', 'standalone'),
                        
                        # 添加存储信息
                        'storage_type': storage_info['storage_type'],
                        'allocated_storage_gb': storage_info['allocated_storage_gb'],
                        'max_allocated_storage_gb': storage_info['max_allocated_storage_gb'],
                        'used_storage_gb': storage_info['used_storage_gb'],
                        'iops': storage_info['iops'],
                        'storage_throughput_mbps': storage_info['storage_throughput_mbps'],
                        'storage_encrypted': storage_info['storage_encrypted']
                    }
                    instances.append(instance_info)
                else:
                    skipped_instances.append({
                        'identifier': db_instance['DBInstanceIdentifier'],
                        'instance_class': instance_class
                    })
                    self.logger.info(f"跳过实例 {db_instance['DBInstanceIdentifier']} (类型: {instance_class})")
            
            self.logger.info(f"找到 {len(instances)} 个符合条件的RDS MySQL实例")
            if skipped_instances:
                self.logger.info(f"跳过 {len(skipped_instances)} 个db.t类型的实例")

            return instances
            
        except Exception as e:
            self.logger.error(f"获取RDS实例失败: {e}")
            return []

    def _determine_architecture_with_taz(self, db_instance: Dict, all_instances: List[Dict], aurora_clusters: Dict) -> str:
        """
        确定数据库实例的架构类型，支持TAZ（三可用区数据库集群部署）
        
        Args:
            db_instance: RDS实例信息
            all_instances: 所有实例列表
            aurora_clusters: Aurora集群信息字典
            
        Returns:
            架构类型: 'single_az', 'multi_az', 'read_replica', 'taz_cluster'
        """
        db_identifier = db_instance['DBInstanceIdentifier']
        cluster_identifier = db_instance.get('DBClusterIdentifier')
        
        # 检查是否是Aurora集群成员
        if cluster_identifier and cluster_identifier in aurora_clusters:
            cluster_info = aurora_clusters[cluster_identifier]
            member_count = len(cluster_info['members'])
            
            # 如果集群有3个或更多成员，认为是TAZ架构
            if member_count >= 3:
                self.logger.info(f"实例 {db_identifier} 属于TAZ集群 {cluster_identifier}，成员数: {member_count}")
                return 'taz_cluster'
            else:
                # 少于3个成员的集群，按原有逻辑处理
                if db_instance.get('MultiAZ', False):
                    return 'multi_az'
                else:
                    return 'single_az'
        
        # 非Aurora集群实例，按原有逻辑处理
        source_db = db_instance.get('ReadReplicaSourceDBInstanceIdentifier')
        
        if source_db and all_instances:
            # 检查是否存在匹配的主实例
            source_exists = any(inst.get('DBInstanceIdentifier') == source_db for inst in all_instances)
            
            if source_exists:
                # 存在匹配的主实例，这是一个read replica
                if db_instance.get('MultiAZ', False):
                    return 'multi_az'
                else:
                    return 'single_az'
            else:
                # 不存在匹配的主实例，这是一个孤儿read replica
                return 'read_replica'
        
        # 没有source_db_instance_identifier，按原逻辑处理
        if db_instance.get('MultiAZ', False):
            return 'multi_az'
        else:
            return 'single_az'

    def _get_cluster_info(self, db_instance: Dict, aurora_clusters: Dict) -> Dict:
        """
        获取实例的集群信息
        
        Args:
            db_instance: RDS实例信息
            aurora_clusters: Aurora集群信息字典
            
        Returns:
            集群信息字典
        """
        cluster_identifier = db_instance.get('DBClusterIdentifier')
        db_identifier = db_instance['DBInstanceIdentifier']
        
        if cluster_identifier and cluster_identifier in aurora_clusters:
            cluster_info = aurora_clusters[cluster_identifier]
            
            # 判断是否是Primary节点
            is_primary = (cluster_info['primary_node'] == db_identifier)
            
            # 确定角色
            if is_primary:
                role = 'primary'
            else:
                role = 'reader'
            
            return {
                'cluster_id': cluster_identifier,
                'is_primary': is_primary,
                'role': role,
                'member_count': len(cluster_info['members']),
                'primary_node_id': cluster_info['primary_node']  # 添加primary节点ID
            }
        else:
            # 非集群实例
            return {
                'cluster_id': 'N/A',
                'is_primary': True,
                'role': 'standalone',
                'member_count': 1,
                'primary_node_id': None  # 非集群实例没有primary节点
            }

    def _should_process_instance(self, instance_class: str) -> bool:
        """
        判断是否应该处理该实例类型
        仅处理db.m和db.r开头的实例，跳过db.t开头的实例
        
        Args:
            instance_class: 实例类型，如 'db.t3.micro', 'db.m6g.large', 'db.r5.xlarge'
            
        Returns:
            True表示应该处理，False表示跳过
        """
        if not instance_class.startswith('db.'):
            return False
        
        # 提取实例族（如 't3', 'm6g', 'r5'）
        instance_family = instance_class.split('.')[1] if len(instance_class.split('.')) > 1 else ''
        
        # 仅处理m和r开头的实例族
        if instance_family.startswith('m') or instance_family.startswith('r'):
            return True
        elif instance_family.startswith('t'):
            return False
        else:
            # 对于其他未知类型，记录警告但仍然处理
            self.logger.warning(f"未知实例族类型: {instance_class}，将继续处理")
            return True

    def get_rds_mysql_pricing(self) -> None:
        """
        获取当前区域所有RDS MySQL实例的1年RI无预付Single-AZ定价
        将所有定价信息存储在pricing_cache中
        """
        if self.pricing_cache:
            self.logger.info("定价缓存已存在，跳过重复获取")
            return
        
        try:
            self.logger.info(f"开始获取区域 {self.region} 的所有RDS MySQL实例定价...")
            
            # 构建过滤器 - 获取所有RDS MySQL实例的定价
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()}
            ]
            
            # 使用分页获取所有产品
            paginator = self.pricing_client.get_paginator('get_products')
            page_iterator = paginator.paginate(
                ServiceCode='AmazonRDS',
                Filters=filters
            )
            
            processed_count = 0
            for page in page_iterator:
                for price_item in page['PriceList']:
                    product = json.loads(price_item)
                    
                    # 获取实例类型
                    attributes = product.get('product', {}).get('attributes', {})
                    instance_type = attributes.get('instanceType')
                    
                    if not instance_type:
                        continue
                    
                    # 只处理db.m和db.r开头的实例类型
                    if not self._should_process_instance(instance_type):
                        continue
                    
                    # 查找1年RI无预付定价
                    terms = product.get('terms', {})
                    reserved_terms = terms.get('Reserved', {})
                    
                    for term_key, term_data in reserved_terms.items():
                        term_attributes = term_data.get('termAttributes', {})
                        if (term_attributes.get('LeaseContractLength') == '1yr' and 
                            term_attributes.get('PurchaseOption') == 'No Upfront'):
                            
                            price_dimensions = term_data.get('priceDimensions', {})
                            for price_key, price_data in price_dimensions.items():
                                price_per_unit = price_data.get('pricePerUnit', {})
                                usd_price = price_per_unit.get('USD')
                                if usd_price:
                                    hourly_rate = float(usd_price)
                                    self.pricing_cache[instance_type] = hourly_rate
                                    processed_count += 1
                                    self.logger.debug(f"缓存定价: {instance_type} = ${hourly_rate}/小时")
                                    break
                            break
            
            self.logger.info(f"定价缓存完成，共缓存 {processed_count} 个实例类型的定价信息")
            
        except Exception as e:
            self.logger.error(f"获取RDS MySQL定价失败: {e}")
            
    def get_instance_pricing_from_cache(self, instance_class: str) -> Optional[float]:
        """
        从pricing_cache中获取指定实例类型的定价
        
        Args:
            instance_class: 实例类型，如 'db.r5.xlarge'
            
        Returns:
            小时费率（美元），如果未找到返回None
        """
        if not self.pricing_cache:
            self.logger.warning("定价缓存为空，请先调用get_rds_mysql_pricing()方法")
            return None
            
        hourly_rate = self.pricing_cache.get(instance_class)
        if hourly_rate:
            self.logger.debug(f"从缓存获取定价: {instance_class} = ${hourly_rate}/小时")
        else:
            self.logger.warning(f"未在缓存中找到实例类型 {instance_class} 的定价")
            
        return hourly_rate

    def map_to_aurora_instance(self, rds_instance_class: str, aurora_generation: str) -> str:
        """
        将RDS实例类型映射到指定代的Aurora实例类型
        支持r6g、r7g、r8g三种Aurora实例类型
        
        Args:
            rds_instance_class: RDS实例类型，如 'db.m6g.2xlarge', 'db.r5.xlarge'
            aurora_generation: Aurora实例代数，如 'r6g', 'r7g', 'r8g'
            
        Returns:
            Aurora实例类型，如 'db.r7g.2xlarge'
        """
        # 移除 'db.' 前缀
        instance_type = rds_instance_class.replace('db.', '')
        
        # 提取大小部分（如 '2xlarge'）
        parts = instance_type.split('.')
        if len(parts) >= 2:
            instance_family = parts[0]  # 如 'm6g', 'r5'
            size = parts[1]             # 如 'xlarge', '2xlarge'
            
            # 验证实例族是否为m或r开头
            if not (instance_family.startswith('m') or instance_family.startswith('r')):
                self.logger.warning(f"不支持的实例族类型 {instance_family}，使用默认值")
                return f"db.{aurora_generation}.large"
            
            # 映射到指定代的Aurora实例
            aurora_instance_class = f"db.{aurora_generation}.{size}"
            self.logger.debug(f"映射 {rds_instance_class} -> {aurora_instance_class}")
            return aurora_instance_class
        else:
            # 如果无法解析，默认返回指定代的large实例
            self.logger.warning(f"无法解析实例类型 {rds_instance_class}，使用默认值 db.{aurora_generation}.large")
            return f"db.{aurora_generation}.large"

    def map_to_rds_replacement_instance(self, rds_instance_class: str, replacement_generation: str) -> str:
        """
        将RDS实例类型映射到指定代的RDS替换实例类型
        支持r7g、r8g两种RDS替换实例类型
        
        Args:
            rds_instance_class: 原RDS实例类型，如 'db.m6g.2xlarge', 'db.r5.xlarge'
            replacement_generation: RDS替换实例代数，如 'r7g', 'r8g'
            
        Returns:
            RDS替换实例类型，如 'db.r7g.2xlarge'
        """
        # 移除 'db.' 前缀
        instance_type = rds_instance_class.replace('db.', '')
        
        # 提取大小部分（如 '2xlarge'）
        parts = instance_type.split('.')
        if len(parts) >= 2:
            instance_family = parts[0]  # 如 'm6g', 'r5'
            size = parts[1]             # 如 'xlarge', '2xlarge'
            
            # 验证实例族是否为m或r开头
            if not (instance_family.startswith('m') or instance_family.startswith('r')):
                self.logger.warning(f"不支持的实例族类型 {instance_family}，使用默认值")
                return f"db.{replacement_generation}.large"
            
            # 映射到指定代的RDS替换实例
            rds_replacement_instance_class = f"db.{replacement_generation}.{size}"
            self.logger.debug(f"RDS替换映射 {rds_instance_class} -> {rds_replacement_instance_class}")
            return rds_replacement_instance_class
        else:
            # 如果无法解析，默认返回指定代的large实例
            self.logger.warning(f"无法解析实例类型 {rds_instance_class}，使用默认值 db.{replacement_generation}.large")
            return f"db.{replacement_generation}.large"

    def get_rds_replacement_mysql_pricing(self, instance_class: str) -> Optional[float]:
        """
        获取RDS替换MySQL实例的1年RI无预付Single-AZ定价
        
        Args:
            instance_class: RDS替换实例类型，如 'db.r7g.xlarge'
            
        Returns:
            小时费率（美元），如果获取失败返回None
        """
        if instance_class in self.pricing_cache:
            return self.pricing_cache[instance_class]
        
        try:
            # 构建过滤器
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'},
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_class},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters
            )
            
            # 查找1年RI无预付定价
            for price_item in response['PriceList']:
                product = json.loads(price_item)
                
                terms = product.get('terms', {})
                reserved_terms = terms.get('Reserved', {})
                
                for term_key, term_data in reserved_terms.items():
                    attributes = term_data.get('termAttributes', {})
                    if (attributes.get('LeaseContractLength') == '1yr' and 
                        attributes.get('PurchaseOption') == 'No Upfront'):
                        
                        price_dimensions = term_data.get('priceDimensions', {})
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            if usd_price:
                                hourly_rate = float(usd_price)
                                self.pricing_cache[instance_class] = hourly_rate
                                self.logger.info(f"RDS替换MySQL {instance_class} RI定价: ${hourly_rate}/小时")
                                return hourly_rate
            
            self.logger.warning(f"未找到RDS替换MySQL {instance_class}的RI定价")
            return None
            
        except Exception as e:
            self.logger.error(f"获取RDS替换MySQL定价失败 {instance_class}: {e}")
            return None
        """
        将RDS实例类型映射到指定代的Aurora实例类型
        支持r6g、r7g、r8g三种Aurora实例类型
        
        Args:
            rds_instance_class: RDS实例类型，如 'db.m6g.2xlarge', 'db.r5.xlarge'
            aurora_generation: Aurora实例代数，如 'r6g', 'r7g', 'r8g'
            
        Returns:
            Aurora实例类型，如 'db.r7g.2xlarge'
        """
        # 移除 'db.' 前缀
        instance_type = rds_instance_class.replace('db.', '')
        
        # 提取大小部分（如 '2xlarge'）
        parts = instance_type.split('.')
        if len(parts) >= 2:
            instance_family = parts[0]  # 如 'm6g', 'r5'
            size = parts[1]             # 如 'xlarge', '2xlarge'
            
            # 验证实例族是否为m或r开头
            if not (instance_family.startswith('m') or instance_family.startswith('r')):
                self.logger.warning(f"不支持的实例族类型 {instance_family}，使用默认值")
                return f"db.{aurora_generation}.large"
            
            # 映射到指定代的Aurora实例
            aurora_instance_class = f"db.{aurora_generation}.{size}"
            self.logger.debug(f"映射 {rds_instance_class} -> {aurora_instance_class}")
            return aurora_instance_class
        else:
            # 如果无法解析，默认返回指定代的large实例
            self.logger.warning(f"无法解析实例类型 {rds_instance_class}，使用默认值 db.{aurora_generation}.large")
            return f"db.{aurora_generation}.large"

    def get_aurora_mysql_pricing(self, instance_class: str) -> Optional[float]:
        """
        获取Aurora MySQL实例的1年RI无预付Single-AZ定价
        
        Args:
            instance_class: Aurora实例类型，如 'db.r7g.xlarge'
            
        Returns:
            小时费率（美元），如果获取失败返回None
        """
        if instance_class in self.aurora_pricing_cache:
            return self.aurora_pricing_cache[instance_class]
        
        try:
            # 构建过滤器
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'servicecode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'Aurora MySQL'},
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_class},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_pricing_location()}
            ]
            
            response = self.pricing_client.get_products(
                ServiceCode='AmazonRDS',
                Filters=filters
            )
            
            # Aurora 实例 single-az 的 standard 的单价
            for price_item in response['PriceList']:
                product = json.loads(price_item)
                
                # 查找1年RI无预付定价
                terms = product.get('terms', {})
                reserved_terms = terms.get('Reserved', {})
                
                for term_key, term_data in reserved_terms.items():
                    attributes = term_data.get('termAttributes', {})
                    if (attributes.get('LeaseContractLength') == '1yr' and 
                        attributes.get('PurchaseOption') == 'No Upfront'):
                        
                        price_dimensions = term_data.get('priceDimensions', {})
                        for price_key, price_data in price_dimensions.items():
                            price_per_unit = price_data.get('pricePerUnit', {})
                            usd_price = price_per_unit.get('USD')
                            if usd_price:
                                hourly_rate = float(usd_price)
                                self.aurora_pricing_cache[instance_class] = hourly_rate
                                self.logger.info(f"Aurora MySQL {instance_class} RI定价: ${hourly_rate}/小时")
                                return hourly_rate
            
            self.logger.warning(f"未找到Aurora MySQL {instance_class}的RI定价")
            return None
            
        except Exception as e:
            self.logger.error(f"获取Aurora MySQL定价失败 {instance_class}: {e}")
            return None

    def _get_pricing_location(self) -> str:
        """
        将AWS区域转换为Pricing API使用的位置名称
        
        Returns:
            位置名称
        """
        region_to_location = {
            "us-east-1": "US East (N. Virginia)",
            "us-east-2": "US East (Ohio)",
            "us-west-1": "US West (N. California)",
            "us-west-2": "US West (Oregon)",
            "ap-east-1": "Asia Pacific (Hong Kong)",
            "ap-south-1": "Asia Pacific (Mumbai)",
            "ap-south-2": "Asia Pacific (Hyderabad)",
            "ap-northeast-1": "Asia Pacific (Tokyo)",
            "ap-northeast-2": "Asia Pacific (Seoul)",
            "ap-northeast-3": "Asia Pacific (Osaka)",
            "ap-southeast-1": "Asia Pacific (Singapore)",
            "ap-southeast-2": "Asia Pacific (Sydney)",
            "ap-southeast-3": "Asia Pacific (Jakarta)",
            "ap-southeast-4": "Asia Pacific (Melbourne)",
            "ca-central-1": "Canada (Central)",
            "eu-central-1": "EU (Frankfurt)",
            "eu-central-2": "EU (Zurich)",
            "eu-west-1": "EU (Ireland)",
            "eu-west-2": "EU (London)",
            "eu-west-3": "EU (Paris)",
            "eu-north-1": "EU (Stockholm)",
            "eu-south-1": "EU (Milan)",
            "eu-south-2": "EU (Spain)",
            "me-south-1": "Middle East (Bahrain)",
            "me-central-1": "Middle East (UAE)",
            "af-south-1": "Africa (Cape Town)",
            "sa-east-1": "South America (Sao Paulo)"
        }
        
        return region_to_location.get(self.region, 'US East (N. Virginia)')

    def calculate_mrr(self, hourly_rate: float) -> float:
        """
        计算月度费用（MRR）
        
        Args:
            hourly_rate: 小时费率
            
        Returns:
            月度费用
        """
        return hourly_rate * 730  # 假设每月30天
    def analyze_instances(self) -> List[Dict]:
        """
        分析所有RDS MySQL实例并计算定价（包括存储成本）
        为每个实例计算r7g、r8g两种Aurora转换成本，分别计算实例MRR、存储MRR和总MRR
        为每个实例计算r7g、r8g两种RDS替换成本，分别计算实例MRR、存储MRR和总MRR
        支持TAZ架构，将存储成本分配到Primary节点
        
        Returns:
            包含完整分析结果的字典列表，包括：
            - Aurora实例MRR（不含存储）
            - Aurora存储MRR
            - Aurora总MRR（实例+存储）
            - RDS替换实例MRR（不含存储）
            - RDS替换存储MRR
            - RDS替换总MRR（实例+存储）
        """
        # 首先获取所有定价信息并缓存
        self.logger.info("开始获取定价信息...")
        self.get_rds_mysql_pricing()
        self.get_all_storage_pricing()  # 一次性获取所有存储类型定价
        self.get_aurora_storage_pricing()  # 一次性获取Aurora存储定价
        
        instances = self.get_all_rds_mysql_instances()  
        results = []
        
        # 按集群分组计算Aurora存储成本
        cluster_aurora_storage_costs = self._calculate_cluster_aurora_storage_costs(instances)
        
        for instance in instances:
            self.logger.info(f"分析实例: {instance['db_instance_identifier']}")
            
            # 从缓存获取RDS MySQL定价
            rds_hourly_rate = self.get_instance_pricing_from_cache(instance['instance_class'])
            
            # 根据架构调整RDS价格
            if instance['architecture'] in ['multi_az', 'taz_cluster'] and rds_hourly_rate:
                if instance['architecture'] == 'taz_cluster':
                    # TAZ集群：每个实例都按单价计算，不需要乘以倍数
                    rds_adjusted_rate = rds_hourly_rate
                    self.logger.info(f"实例 {instance['db_instance_identifier']} 是TAZ集群成员，使用单价")
                else:
                    # Multi-AZ：价格乘以2
                    rds_adjusted_rate = rds_hourly_rate * 2
                    self.logger.info(f"实例 {instance['db_instance_identifier']} 是multi_az，RDS成本乘以2")
            else:
                rds_adjusted_rate = rds_hourly_rate
            
            # 从缓存获取存储定价
            storage_type = instance['storage_type']
            storage_pricing = self.get_storage_pricing(storage_type)
            
            # 构建存储信息字典，包含storage_type用于GP3 baseline计算
            storage_info = {
                'storage_type': storage_type,
                'allocated_storage_gb': instance['allocated_storage_gb'],
                'iops': instance['iops'],
                'storage_throughput_mbps': instance['storage_throughput_mbps']
            }
            
            # 计算存储成本（RDS场景，Multi-AZ需要乘以2）
            is_multi_az = instance['architecture'] == 'multi_az'
            storage_cost = self.calculate_storage_cost(storage_info, storage_pricing, is_multi_az, is_aurora_migration=False)
            
            # 获取Aurora存储成本信息（支持RDS MySQL集群和TAZ架构）
            # 使用新的集群ID确定逻辑
            rds_clusters = self._identify_rds_mysql_clusters(instances)
            cluster_id = self._determine_cluster_id(instance, rds_clusters)
            cluster_aurora_cost = cluster_aurora_storage_costs.get(cluster_id, {})
            
            # 判断当前实例是否为集群的primary节点
            # 获取集群中的所有实例来进行判断
            cluster_instances = []
            for inst in instances:
                if self._determine_cluster_id(inst, rds_clusters) == cluster_id:
                    cluster_instances.append(inst)
            
            is_primary = self._is_primary_instance(instance, cluster_instances)
            
            # 根据实例在集群中的角色决定Aurora存储成本分配
            if cluster_aurora_cost.get('is_rds_mysql_cluster', False):
                # RDS MySQL集群：只有Primary节点承担存储成本
                if is_primary:
                    aurora_storage_cost_fields = {
                        'aurora_allocate_storage_gb': cluster_aurora_cost.get('aurora_storage_gb', 0),
                        'aurora_total_storage_cost_per_month_usd': cluster_aurora_cost.get('aurora_total_storage_cost_per_month', 0),
                        'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                    }
                    self.logger.info(f"RDS MySQL集群Primary节点 {instance['db_instance_identifier']} 承担存储成本: "
                                   f"${cluster_aurora_cost.get('aurora_total_storage_cost_per_month', 0)}")
                else:
                    # Read replica节点：Aurora存储成本填0
                    aurora_storage_cost_fields = {
                        'aurora_allocate_storage_gb': 0,
                        'aurora_total_storage_cost_per_month_usd': 0,
                        'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                    }
                    self.logger.info(f"RDS MySQL集群Read Replica节点 {instance['db_instance_identifier']} 不承担存储成本")
            elif instance['architecture'] == 'taz_cluster':
                # TAZ集群：只有Primary节点承担存储成本
                if instance.get('is_cluster_primary', False):
                    aurora_storage_cost_fields = {
                        'aurora_allocate_storage_gb': cluster_aurora_cost.get('aurora_storage_gb', 0),
                        'aurora_total_storage_cost_per_month_usd': cluster_aurora_cost.get('aurora_total_storage_cost_per_month', 0),
                        'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                    }
                    self.logger.info(f"TAZ集群Primary节点 {instance['db_instance_identifier']} 承担存储成本: "
                                   f"${cluster_aurora_cost.get('aurora_total_storage_cost_per_month', 0)}")
                else:
                    # Reader节点：Aurora存储成本填0
                    aurora_storage_cost_fields = {
                        'aurora_allocate_storage_gb': 0,
                        'aurora_total_storage_cost_per_month_usd': 0,
                        'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                    }
                    self.logger.info(f"TAZ集群Reader节点 {instance['db_instance_identifier']} 不承担存储成本")
            elif is_primary:
                # 其他架构的主实例：显示完整的Aurora存储成本
                aurora_storage_cost_fields = {
                    'aurora_allocate_storage_gb': cluster_aurora_cost.get('aurora_storage_gb', 0),
                    'aurora_total_storage_cost_per_month_usd': cluster_aurora_cost.get('aurora_total_storage_cost_per_month', 0),
                    'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                }
            else:
                # Read replica：Aurora存储成本填0
                aurora_storage_cost_fields = {
                    'aurora_allocate_storage_gb': 0,
                    'aurora_total_storage_cost_per_month_usd': 0,
                    'aurora_storage_price_per_gb_month_usd': cluster_aurora_cost.get('aurora_storage_price_per_gb_month', 0)
                }
            
            # 计算RDS总MRR（实例MRR + 存储MRR）
            rds_mrr = round(self.calculate_mrr(rds_adjusted_rate), 2) if rds_adjusted_rate else 'NA'
            total_storage_cost = storage_cost.get('total_storage_cost_per_month', 'NA')
            
            if rds_mrr != 'NA' and total_storage_cost != 'NA':
                rds_total_mrr = round(rds_mrr + total_storage_cost, 2)
                self.logger.info(f"实例 {instance['db_instance_identifier']} RDS总MRR: "
                               f"实例MRR=${rds_mrr} + 存储MRR=${total_storage_cost} = ${rds_total_mrr}")
            else:
                rds_total_mrr = 'NA'
                self.logger.warning(f"实例 {instance['db_instance_identifier']} 无法计算RDS总MRR，"
                                  f"实例MRR={rds_mrr}, 存储MRR={total_storage_cost}")
            
            # 构建基础结果
            result = {
                'account_id': instance['account_id'],
                'region': instance['region'],
                'mysql_engine_version': instance['mysql_engine_version'],
                'db_instance_identifier': instance['db_instance_identifier'],
                'source_db_instance_identifier': instance['source_db_instance_identifier'],
                'architecture': instance['architecture'],
                'rds_instance_class': instance['instance_class'],
                'rds_hourly_rate_usd': rds_adjusted_rate if rds_adjusted_rate else 'NA',
                'rds_mrr_usd': rds_mrr,
                
                # 集群信息
                #'cluster_identifier': cluster_id,
                #'cluster_role': instance.get('cluster_role', 'standalone'),
                #'is_cluster_primary': instance.get('is_cluster_primary', True),
                
                # 存储信息
                'storage_type': storage_type,
                'allocated_storage_gb': instance['allocated_storage_gb'],
                'used_storage_gb': instance['used_storage_gb'],
                'iops': instance['iops'],
                'storage_throughput_mbps': instance['storage_throughput_mbps'],
                
                # 存储定价
                'storage_price_per_gb_month_usd': storage_pricing.get('storage_price_per_gb_month', 'NA'),
                'iops_price_per_iops_month_usd': storage_pricing.get('iops_price_per_iops_month', 'NA'),
                #'throughput_price_per_mbps_month_usd': storage_pricing.get('throughput_price_per_mbps_month', 'NA'),
                
                # 存储成本
                'storage_cost_per_month_usd': storage_cost.get('storage_cost_per_month', 'NA'),
                'iops_cost_per_month_usd': storage_cost.get('iops_cost_per_month', 'NA'),
                #'throughput_cost_per_month_usd': storage_cost.get('throughput_cost_per_month', 'NA'),
                'total_storage_cost_per_month_usd': total_storage_cost,
                
                # rds 总成本
                'rds_total_mrr_usd': rds_total_mrr,  # 新增字段：RDS总MRR（实例+存储）

                # GP3 baseline超出信息
                #'gp3_baseline_exceeded_iops': storage_cost.get('gp3_baseline_exceeded_iops', 0),
                #'gp3_baseline_exceeded_throughput': storage_cost.get('gp3_baseline_exceeded_throughput', 0)
            }
            
            # 添加Aurora存储成本字段
            result.update(aurora_storage_cost_fields)
            
            # 为每种Aurora实例代数计算转换成本
            for generation in self.aurora_generations:
                self.logger.info(f"为实例 {instance['db_instance_identifier']} 计算Aurora {generation}转换成本")
                
                # 映射到指定代的Aurora实例
                aurora_instance_class = self.map_to_aurora_instance(instance['instance_class'], generation)
                
                # 获取Aurora MySQL定价
                aurora_hourly_rate = self.get_aurora_mysql_pricing(aurora_instance_class)
                
                # 根据架构调整Aurora价格
                #if instance['architecture'] in ['multi_az', 'taz_cluster'] and aurora_hourly_rate:
                #    if instance['architecture'] == 'taz_cluster':
                #        # TAZ集群：每个实例都按单价计算
                #        aurora_adjusted_rate = aurora_hourly_rate
                #        self.logger.info(f"实例 {instance['db_instance_identifier']} 是TAZ集群成员，Aurora {generation}使用单价")
                #    else:
                #        # Multi-AZ：价格乘以2
                #        aurora_adjusted_rate = aurora_hourly_rate
                #        print("#######")
                #        print(aurora_adjusted_rate)
                #        self.logger.info(f"实例 {instance['db_instance_identifier']} 是multi_az，Aurora {generation}使用单价")
                #else:
                aurora_adjusted_rate = aurora_hourly_rate
                
                # 计算Aurora IO Optimized实例MRR（不包含存储）
                aurora_instance_mrr = round(self.calculate_mrr(aurora_adjusted_rate*1.3), 2) if aurora_adjusted_rate else 'NA'
                
                # 获取Aurora存储成本（支持RDS MySQL集群、TAZ架构和其他架构）
                aurora_storage_mrr = 0
                
                # 检查是否为RDS MySQL集群的Primary节点
                if (cluster_aurora_cost.get('is_rds_mysql_cluster', False) and 
                    is_primary and 
                    aurora_storage_cost_fields.get('aurora_total_storage_cost_per_month_usd', 0) > 0):
                    
                    aurora_storage_mrr = aurora_storage_cost_fields['aurora_total_storage_cost_per_month_usd']
                    self.logger.info(f"RDS MySQL集群Primary节点 {instance['db_instance_identifier']} "
                                   f"Aurora {generation} 存储成本: ${aurora_storage_mrr}")
                
                # 检查是否为TAZ集群的Primary节点
                elif (instance['architecture'] == 'taz_cluster' and 
                      instance.get('is_cluster_primary', False) and 
                      aurora_storage_cost_fields.get('aurora_total_storage_cost_per_month_usd', 0) > 0):
                    
                    aurora_storage_mrr = aurora_storage_cost_fields['aurora_total_storage_cost_per_month_usd']
                    self.logger.info(f"TAZ集群Primary节点 {instance['db_instance_identifier']} "
                                   f"Aurora {generation} 存储成本: ${aurora_storage_mrr}")
                
                # 检查是否为其他架构的Primary节点
                elif (is_primary and 
                      aurora_storage_cost_fields.get('aurora_total_storage_cost_per_month_usd', 0) > 0):
                    
                    aurora_storage_mrr = aurora_storage_cost_fields['aurora_total_storage_cost_per_month_usd']
                    self.logger.info(f"Primary节点 {instance['db_instance_identifier']} "
                                   f"Aurora {generation} 存储成本: ${aurora_storage_mrr}")
                
                # 计算总MRR（实例成本 + 存储成本）
                if aurora_instance_mrr != 'NA':
                    aurora_total_mrr = round(aurora_instance_mrr + aurora_storage_mrr, 2)
                else:
                    aurora_total_mrr = 'NA'
                
                # 添加到结果中
                result[f'aurora_{generation}_instance_class'] = aurora_instance_class
                result[f'aurora_{generation}_hourly_rate_usd'] = aurora_adjusted_rate*1.3 if aurora_adjusted_rate else 'NA'
                result[f'aurora_{generation}_instance_mrr_usd'] = aurora_instance_mrr
                result[f'aurora_{generation}_storage_mrr_usd'] = round(aurora_storage_mrr, 2) if aurora_storage_mrr > 0 else 0
                result[f'aurora_{generation}_total_mrr_usd'] = aurora_total_mrr
            
            # 为每种RDS替换实例代数计算成本
            for generation in self.rds_replacement_generations:
                self.logger.info(f"为实例 {instance['db_instance_identifier']} 计算RDS替换 {generation}成本")
                
                # 映射到指定代的RDS替换实例
                rds_replacement_instance_class = self.map_to_rds_replacement_instance(instance['instance_class'], generation)
                
                # 获取RDS替换MySQL定价
                rds_replacement_hourly_rate = self.get_rds_replacement_mysql_pricing(rds_replacement_instance_class)
                
                # 根据架构调整RDS替换价格
                if instance['architecture'] in ['multi_az', 'taz_cluster'] and rds_replacement_hourly_rate:
                    if instance['architecture'] == 'taz_cluster':
                        # TAZ集群：每个实例都按单价计算
                        rds_replacement_adjusted_rate = rds_replacement_hourly_rate
                        self.logger.info(f"实例 {instance['db_instance_identifier']} 是TAZ集群成员，RDS替换 {generation}使用单价")
                    else:
                        # Multi-AZ：价格乘以2
                        rds_replacement_adjusted_rate = rds_replacement_hourly_rate * 2
                        self.logger.info(f"实例 {instance['db_instance_identifier']} 是multi_az，RDS替换 {generation}成本乘以2")
                else:
                    rds_replacement_adjusted_rate = rds_replacement_hourly_rate
                
                # 计算RDS替换实例MRR
                rds_replacement_instance_mrr = round(self.calculate_mrr(rds_replacement_adjusted_rate), 2) if rds_replacement_adjusted_rate else 'NA'
                
                # 计算RDS替换存储成本（使用相同的存储配置）
                # 对于Multi-AZ架构，存储成本需要乘以2（RDS替换场景，非Aurora迁移）
                if instance['architecture'] == 'multi_az':
                    rds_replacement_storage_cost = self.calculate_storage_cost(storage_info, storage_pricing, True, is_aurora_migration=False)
                    self.logger.info(f"实例 {instance['db_instance_identifier']} 是multi_az，RDS替换 {generation}存储成本乘以2")
                else:
                    rds_replacement_storage_cost = self.calculate_storage_cost(storage_info, storage_pricing, False, is_aurora_migration=False)
                
                rds_replacement_storage_mrr = rds_replacement_storage_cost.get('total_storage_cost_per_month', 0)
                
                # 计算总MRR（实例成本 + 存储成本）
                if rds_replacement_instance_mrr != 'NA':
                    rds_replacement_total_mrr = round(rds_replacement_instance_mrr + rds_replacement_storage_mrr, 2)
                else:
                    rds_replacement_total_mrr = 'NA'
                
                # 添加到结果中
                result[f'rds_replacement_{generation}_instance_class'] = rds_replacement_instance_class
                result[f'rds_replacement_{generation}_hourly_rate_usd'] = rds_replacement_adjusted_rate if rds_replacement_adjusted_rate else 'NA'
                result[f'rds_replacement_{generation}_instance_mrr_usd'] = rds_replacement_instance_mrr
                result[f'rds_replacement_{generation}_storage_mrr_usd'] = round(rds_replacement_storage_mrr, 2) if rds_replacement_storage_mrr > 0 else 0
                result[f'rds_replacement_{generation}_total_mrr_usd'] = rds_replacement_total_mrr
            
            results.append(result)
        
        return results

    def _calculate_cluster_aurora_storage_costs(self, instances: List[Dict]) -> Dict[str, Dict]:
        """
        按集群计算Aurora存储成本
        对于Multi-AZ架构，存储成本仅计算一份并分配到Primary节点
        对于RDS MySQL集群（通过source_db_instance_identifier识别），存储成本仅计算一次并加和到Primary节点
        
        Args:
            instances: 所有实例列表
            
        Returns:
            集群Aurora存储成本字典，key为集群ID，value为成本信息
        """
        cluster_costs = {}
        aurora_storage_pricing = self.get_aurora_storage_pricing()
        
        # 按集群分组实例（包括RDS MySQL集群和Aurora集群）
        clusters = {}
        
        # 首先识别RDS MySQL集群（基于source_db_instance_identifier）
        rds_clusters = self._identify_rds_mysql_clusters(instances)
        
        for instance in instances:
            # 确定集群ID
            cluster_id = self._determine_cluster_id(instance, rds_clusters)
            
            if cluster_id not in clusters:
                clusters[cluster_id] = []
            clusters[cluster_id].append(instance)
        
        # 为每个集群计算Aurora存储成本
        for cluster_id, cluster_instances in clusters.items():
            # 计算集群的总存储需求（基于实际使用量）
            total_used_storage_gb = 0
            is_multi_az = False
            has_read_replicas = False
            primary_instance = None
            
            # 分析集群架构和存储需求
            total_used_storage_gb = 0
            is_multi_az = False
            has_read_replicas = False
            primary_instance = None
            
            for instance in cluster_instances:
                # 检查是否有Multi-AZ实例
                if instance.get('architecture') == 'multi_az':
                    is_multi_az = True
                
                # 检查是否有read replica
                source_db = instance.get('source_db_instance_identifier')
                if source_db not in ['N/A', None, 'writer-node']:
                    has_read_replicas = True
                
                # 识别primary实例
                if self._is_primary_instance(instance, cluster_instances):
                    primary_instance = instance
            
            # 仅计算primary节点的存储成本（Aurora共享存储特性）
            if primary_instance:
                used_storage = primary_instance.get('used_storage_gb', 0)
                allocated_storage = primary_instance.get('allocated_storage_gb', 0)
                
                # 优先使用primary节点的实际使用存储量
                if isinstance(used_storage, (int, float)) and used_storage > 0:
                    total_used_storage_gb = used_storage
                    self.logger.info(f"使用Primary节点 {primary_instance.get('db_instance_identifier')} 的实际使用存储: {used_storage}GB")
                elif isinstance(allocated_storage, (int, float)) and allocated_storage > 0:
                    total_used_storage_gb = allocated_storage
                    self.logger.warning(f"Primary节点 {primary_instance.get('db_instance_identifier')} 未获取到used_storage_gb，使用allocated_storage_gb: {allocated_storage}GB")
                else:
                    self.logger.error(f"Primary节点 {primary_instance.get('db_instance_identifier')} 无法获取存储信息")
            else:
                self.logger.error(f"集群 {cluster_id} 未找到Primary节点，无法计算存储成本")
            
            # Aurora获取存储单价
            storage_price = aurora_storage_pricing.get('storage_price_per_gb_month', 0)
            
            # Aurora存储成本计算逻辑
            # 对于RDS MySQL集群迁移到Aurora，存储成本基于实际使用量计算
            total_aurora_storage_cost_per_month = total_used_storage_gb * storage_price
            
            # 记录存储成本分配策略
            if len(cluster_instances) > 1:
                if is_multi_az and has_read_replicas:
                    self.logger.info(f"集群 {cluster_id} 为Multi-AZ架构且有read replica，"
                                   f"Aurora存储成本基于Primary节点实际使用量({total_used_storage_gb}GB)计算")
                elif has_read_replicas:
                    self.logger.info(f"RDS MySQL集群 {cluster_id} 有read replica，"
                                   f"Aurora存储成本基于Primary节点实际使用量({total_used_storage_gb}GB)计算")
                elif is_multi_az:
                    self.logger.info(f"集群 {cluster_id} 为Multi-AZ架构，"
                                   f"Aurora存储成本基于Primary节点实际使用量({total_used_storage_gb}GB)计算")
            else:
                self.logger.info(f"独立实例 {cluster_id}，"
                               f"Aurora存储成本基于实际使用量({total_used_storage_gb}GB)计算")
            
            cost_info = {
                'aurora_storage_gb': total_used_storage_gb,  # 使用实际使用量
                'aurora_total_storage_cost_per_month': round(total_aurora_storage_cost_per_month, 2),
                'aurora_storage_price_per_gb_month': storage_price,
                'cluster_instance_count': len(cluster_instances),
                'cluster_has_multi_az': is_multi_az,
                'cluster_has_read_replicas': has_read_replicas,
                'primary_instance_id': primary_instance.get('db_instance_identifier') if primary_instance else None,
                'is_rds_mysql_cluster': len(cluster_instances) > 1 and any(
                    inst.get('source_db_instance_identifier') not in ['N/A', None, 'writer-node'] 
                    for inst in cluster_instances
                )
            }
            
            cluster_costs[cluster_id] = cost_info
            
            self.logger.info(f"集群 {cluster_id} Aurora存储成本: "
                           f"Primary节点存储={total_used_storage_gb}GB, "
                           f"总成本=${cost_info['aurora_total_storage_cost_per_month']}/月, "
                           f"Multi-AZ={is_multi_az}, Read Replicas={has_read_replicas}, "
                           f"RDS MySQL集群={cost_info['is_rds_mysql_cluster']}")
        
        return cluster_costs

    def _identify_rds_mysql_clusters(self, instances: List[Dict]) -> Dict[str, List[Dict]]:
        """
        识别RDS MySQL集群（基于source_db_instance_identifier）
        
        Args:
            instances: 所有实例列表
            
        Returns:
            RDS MySQL集群字典，key为primary实例ID，value为集群实例列表
        """
        rds_clusters = {}
        
        # 创建实例映射
        instance_map = {inst['db_instance_identifier']: inst for inst in instances}
        
        for instance in instances:
            source_db = instance.get('source_db_instance_identifier')
            
            # 如果有source_db_instance_identifier且不是特殊值
            if source_db and source_db not in ['N/A', 'writer-node']:
                # 检查source实例是否存在于当前实例列表中
                if source_db in instance_map:
                    primary_instance = instance_map[source_db]
                    primary_id = primary_instance['db_instance_identifier']
                    
                    # 初始化集群
                    if primary_id not in rds_clusters:
                        rds_clusters[primary_id] = [primary_instance]
                    
                    # 添加read replica到集群
                    if instance not in rds_clusters[primary_id]:
                        rds_clusters[primary_id].append(instance)
                    
                    self.logger.info(f"识别到RDS MySQL集群: Primary={primary_id}, "
                                   f"Read Replica={instance['db_instance_identifier']}")
        
        return rds_clusters

    def _determine_cluster_id(self, instance: Dict, rds_clusters: Dict[str, List[Dict]]) -> str:
        """
        确定实例的集群ID
        
        Args:
            instance: 实例信息
            rds_clusters: RDS MySQL集群字典
            
        Returns:
            集群ID
        """
        instance_id = instance['db_instance_identifier']
        
        # 首先检查是否是Aurora集群成员
        aurora_cluster_id = instance.get('cluster_identifier')
        if aurora_cluster_id and aurora_cluster_id != 'N/A':
            return aurora_cluster_id
        
        # 检查是否是RDS MySQL集群的primary节点
        if instance_id in rds_clusters:
            return f"rds_cluster_{instance_id}"
        
        # 检查是否是RDS MySQL集群的read replica
        for primary_id, cluster_instances in rds_clusters.items():
            if instance in cluster_instances and instance_id != primary_id:
                return f"rds_cluster_{primary_id}"
        
        # 独立实例
        return instance_id

    def _is_primary_instance(self, instance: Dict, cluster_instances: List[Dict]) -> bool:
        """
        判断实例是否为集群的primary节点
        
        Args:
            instance: 实例信息
            cluster_instances: 集群中的所有实例
            
        Returns:
            是否为primary节点
        """
        instance_id = instance['db_instance_identifier']
        
        # 对于Aurora集群，使用is_cluster_primary字段
        if instance.get('cluster_identifier') and instance.get('cluster_identifier') != 'N/A':
            return instance.get('is_cluster_primary', False)
        
        # 对于RDS MySQL集群，primary节点是没有source_db_instance_identifier的节点
        # 或者是其他节点的source_db_instance_identifier指向的节点
        source_db = instance.get('source_db_instance_identifier')
        if source_db in ['N/A', None, 'writer-node']:
            # 检查是否有其他实例指向这个实例
            for other_instance in cluster_instances:
                if (other_instance != instance and 
                    other_instance.get('source_db_instance_identifier') == instance_id):
                    return True
            # 如果只有一个实例，那它就是primary
            return len(cluster_instances) == 1
        
        return False

    def export_to_csv(self, results: List[Dict], output_file: str):
        """
        将分析结果导出到CSV文件（包含存储信息和TAZ支持）
        
        Args:
            results: 分析结果列表
            output_file: 输出文件路径
        """
        if not results:
            self.logger.warning("没有数据可导出")
            return
        
        # 构建字段名列表，包含所有Aurora代数的字段和存储信息
        fieldnames = [
            'account_id', 
            'region',
            'mysql_engine_version',
            'db_instance_identifier',
            'source_db_instance_identifier',
            'architecture',
            'rds_instance_class',
            'rds_hourly_rate_usd',
            'rds_mrr_usd',
            
            # 集群信息字段
            #'cluster_identifier',
            #'cluster_role',
            #'is_cluster_primary',
            
            # 存储信息字段
            'storage_type',
            'allocated_storage_gb',
            'used_storage_gb',
            'iops',
            'storage_throughput_mbps',
            
            # 存储定价字段
            'storage_price_per_gb_month_usd',
            'iops_price_per_iops_month_usd',
            #'throughput_price_per_mbps_month_usd',
            
            # 存储成本字段
            'storage_cost_per_month_usd',
            'iops_cost_per_month_usd',
            #'throughput_cost_per_month_usd',
            'total_storage_cost_per_month_usd',

            # rds 总成本
            'rds_total_mrr_usd',  # 新增字段：RDS总MRR（实例+存储）

            # GP3 baseline超出信息字段
            #'gp3_baseline_exceeded_iops',
            #'gp3_baseline_exceeded_throughput',
            
            # Aurora存储成本字段
            'aurora_allocate_storage_gb',
            'aurora_storage_price_per_gb_month_usd',
            'aurora_total_storage_cost_per_month_usd'
        ]
        
        # 为每种Aurora代数添加字段（r7g和r8g）
        for generation in self.aurora_generations:
            fieldnames.extend([
                f'aurora_{generation}_instance_class',
                f'aurora_{generation}_hourly_rate_usd',
                f'aurora_{generation}_instance_mrr_usd',
                f'aurora_{generation}_storage_mrr_usd',
                f'aurora_{generation}_total_mrr_usd'
            ])
        
        # 为每种RDS替换代数添加字段（r7g和r8g）
        for generation in self.rds_replacement_generations:
            fieldnames.extend([
                f'rds_replacement_{generation}_instance_class',
                f'rds_replacement_{generation}_hourly_rate_usd',
                f'rds_replacement_{generation}_instance_mrr_usd',
                f'rds_replacement_{generation}_storage_mrr_usd',
                f'rds_replacement_{generation}_total_mrr_usd'
            ])
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)
            
            self.logger.info(f"结果已导出到: {output_file}")
            
        except Exception as e:
            self.logger.error(f"导出CSV失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='RDS MySQL和Aurora MySQL定价分析工具 - TAZ支持版本（r7g/r8g专版）')
    parser.add_argument('region', help='AWS区域名称 (如: us-east-1)')
    parser.add_argument('-o', '--output', default='rds_aurora_r7g_r8g_pricing_analysis_taz.csv', 
                       help='输出CSV文件名 (默认: rds_aurora_r7g_r8g_pricing_analysis_taz.csv)')
    
    args = parser.parse_args()
    
    try:
        # 创建分析器
        analyzer = RDSAuroraMultiGenerationPricingAnalyzer(args.region)
        
        # 执行分析
        print(f"开始分析区域 {args.region} 的RDS MySQL实例...")
        print("将计算Aurora r7g、r8g两种实例类型的转换成本")
        print("将计算RDS替换r7g、r8g两种实例类型的成本")
        print("分别计算实例MRR、存储MRR和总MRR成本")
        print("包含存储类型、容量、IOPS、带宽和存储成本分析")
        print("支持TAZ（三可用区数据库集群部署）架构")
        results = analyzer.analyze_instances()
        
        if results:
            # 导出结果
            analyzer.export_to_csv(results, args.output)
            print(f"分析完成！共处理 {len(results)} 个实例，结果已保存到 {args.output}")
            print("RDS成本包含：")
            print("- 实例MRR：RDS实例的月度费用（不含存储）")
            print("- 存储MRR：RDS存储的月度费用")
            print("- 总MRR：实例MRR + 存储MRR")
            print("Aurora转换成本包含：")
            print("- 实例MRR：Aurora实例的月度费用（不含存储）")
            print("- 存储MRR：Aurora存储的月度费用（基于Primary节点的used_storage_gb）")
            print("- 总MRR：实例MRR + 存储MRR")
            print("RDS替换成本包含：")
            print("- 实例MRR：RDS替换实例的月度费用（不含存储）")
            print("- 存储MRR：RDS替换存储的月度费用")
            print("- 总MRR：实例MRR + 存储MRR")
            print("存储成本分配规则：")
            print("- RDS场景：Multi-AZ实例存储成本×2")
            print("- Aurora迁移场景：Multi-AZ实例存储成本仅计算一份，不乘以2")
            print("- TAZ集群存储成本仅分配到Primary节点")
            print("- Multi-AZ + Read Replica迁移到Aurora时，存储成本仅分配到Primary节点，计算一份")
            print("- RDS MySQL集群：通过source_db_instance_identifier识别集群关系")
            print("- RDS MySQL集群迁移到Aurora：存储成本仅计算一次，加和到Primary节点")
            print("- Aurora存储成本基于Primary节点的实际使用量(used_storage_gb)计算")
            print("- 符合Aurora共享存储特性，不累加集群中所有节点的存储量")
            print("- Read Replica节点的Aurora存储成本为0，避免重复计算")
            print("- 计算r7g和r8g两种实例类型的转换/替换成本")
        else:
            print("未找到任何RDS MySQL实例")
            
    except NoCredentialsError:
        print("错误: 未找到AWS凭证。请配置AWS凭证后重试。")
        sys.exit(1)
    except ClientError as e:
        print(f"AWS API错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

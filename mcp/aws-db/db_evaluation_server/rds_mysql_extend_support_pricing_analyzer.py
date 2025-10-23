#!/usr/bin/env python3
"""
RDS MySQL实例定价分析脚本 - API版本
通过AWS Pricing API获取所有region的Extended Support定价
"""

import boto3
import json
import csv
import argparse
from datetime import datetime
from typing import Dict, List, Any
import sys

class RDSPricingAnalyzer:
    def __init__(self, region: str):
        self.region = region
        self.rds_client = boto3.client('rds', region_name=region)
        self.pricing_client = boto3.client('pricing', region_name='us-east-1')
        self.sts_client = boto3.client('sts', region_name=region)
        
        # 缓存
        self.cpu_cores_cache = {}
        self._extended_support_cache = {}

    def get_extended_support_pricing(self, cpu_cores: int) -> Dict[str, float]:
        """通过AWS Pricing API获取Extended Support每核心每小时的定价"""
        cache_key = f"extended_support_{self.region}"
        if cache_key in self._extended_support_cache:
            return self._extended_support_cache[cache_key]
        
        try:
            print(f"正在获取 {self.region} 的Extended Support定价...")
            
            # 使用分页获取所有Extended Support相关产品
            paginator = self.pricing_client.get_paginator('get_products')
            page_iterator = paginator.paginate(
                ServiceCode='AmazonRDS',
                Filters=[
                    {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'}
                ]
            )
            
            pricing_data = {
                'year1_per_core_per_hour': 0.0,
                'year2_per_core_per_hour': 0.0,
                'year3_per_core_per_hour': 0.0,
            }
            
            location = self._get_location_name()
            
            for page in page_iterator:
                for product_str in page['PriceList']:
                    product = json.loads(product_str)
                    attributes = product['product']['attributes']
                    
                    # 检查是否为Extended Support产品且匹配当前region
                    usage_type = attributes.get('usagetype', '')
                    product_location = attributes.get('location', '')
                    
                    if 'ExtendedSupport' in usage_type and product_location == location:
                        # 只获取标准版Extended Support定价，过滤特殊后缀版本
                        if ':PP' in usage_type or ':Gov' in usage_type or ':Spot' in usage_type:
                            continue
                        
                        # 获取定价
                        terms = product.get('terms', {}).get('OnDemand', {})
                        
                        for term_key, term_data in terms.items():
                            price_dimensions = term_data.get('priceDimensions', {})
                            for price_key, price_data in price_dimensions.items():
                                price_per_unit = price_data.get('pricePerUnit', {}).get('USD', '0')
                                
                                if float(price_per_unit) > 0:
                                    price_value = float(price_per_unit)
                                    
                                    # 根据usage_type判断年份
                                    if 'Yr1-Yr2' in usage_type:
                                        pricing_data['year1_per_core_per_hour'] = price_value
                                        pricing_data['year2_per_core_per_hour'] = price_value
                                    elif 'Yr3' in usage_type:
                                        pricing_data['year3_per_core_per_hour'] = price_value
            
            # 缓存结果
            self._extended_support_cache[cache_key] = pricing_data
            
            # 如果没有找到定价，返回NA
            if all(price == 0.0 for price in pricing_data.values()):
                pricing_data = {
                    'year1_per_core_per_hour': 'NA',
                    'year2_per_core_per_hour': 'NA',
                    'year3_per_core_per_hour': 'NA',
                }
                print(f"警告: 无法从API获取 {self.region} 的Extended Support定价")
            else:
                print(f"成功获取 {self.region} 的Extended Support定价: Year1-2=${pricing_data['year1_per_core_per_hour']}, Year3=${pricing_data['year3_per_core_per_hour']}")
            
            return pricing_data
            
        except Exception as e:
            print(f"获取Extended Support定价失败: {e}")
            return {
                'year1_per_core_per_hour': 'NA',
                'year2_per_core_per_hour': 'NA',
                'year3_per_core_per_hour': 'NA',
            }

    def get_instance_cpu_cores(self, instance_class: str) -> int:
        """获取实例类型的CPU核心数"""
        if instance_class in self.cpu_cores_cache:
            return self.cpu_cores_cache[instance_class]
        
        try:
            # 从实例类型名称推断CPU核心数
            cpu_cores = self._infer_cpu_cores_from_instance_name(instance_class)
            if cpu_cores > 0:
                self.cpu_cores_cache[instance_class] = cpu_cores
                return cpu_cores
            
            # 使用默认值
            self.cpu_cores_cache[instance_class] = 2
            return 2
            
        except Exception as e:
            print(f"获取实例类型 {instance_class} 的CPU核心数失败: {e}")
            self.cpu_cores_cache[instance_class] = 2
            return 2

    def _infer_cpu_cores_from_instance_name(self, instance_class: str) -> int:
        """从实例类型名称推断CPU核心数"""
        try:
            parts = instance_class.split('.')
            if len(parts) != 3:
                return 0
            
            family = parts[1]
            size = parts[2]
            
            size_mapping = {
                'nano': 1, 'micro': 1, 'small': 1, 'medium': 1, 'large': 2,
                'xlarge': 4, '2xlarge': 8, '3xlarge': 12, '4xlarge': 16,
                '6xlarge': 24, '8xlarge': 32, '9xlarge': 36, '10xlarge': 40,
                '12xlarge': 48, '16xlarge': 64, '18xlarge': 72, '24xlarge': 96,
                '32xlarge': 128, '48xlarge': 192,
            }
            
            if family.startswith('t'):
                if size in ['micro', 'small', 'medium', 'large']:
                    return 2
                elif size == 'xlarge':
                    return 4
                elif size == '2xlarge':
                    return 8
            
            return size_mapping.get(size, 2)
            
        except Exception as e:
            print(f"从实例名称推断CPU核心数失败 {instance_class}: {e}")
            return 0

    def get_account_id(self) -> str:
        """获取当前AWS账户ID"""
        try:
            response = self.sts_client.get_caller_identity()
            return response['Account']
        except Exception as e:
            print(f"获取账户ID失败: {e}")
            return "unknown"

    def get_rds_instances(self) -> List[Dict[str, Any]]:
        """获取指定region下的所有RDS MySQL实例"""
        instances = []
        try:
            paginator = self.rds_client.get_paginator('describe_db_instances')
            
            for page in paginator.paginate():
                for db_instance in page['DBInstances']:
                    if db_instance['Engine'].lower() == 'mysql':
                        architecture = self._determine_architecture(db_instance)
                        
                        instance_info = {
                            'db_instance_identifier': db_instance['DBInstanceIdentifier'],
                            'account_id': self.get_account_id(),
                            'region': self.region,
                            'engine_version': db_instance['EngineVersion'],
                            'architecture': architecture,
                            'instance_class': db_instance['DBInstanceClass'],
                            'cpu_cores': self.get_instance_cpu_cores(db_instance['DBInstanceClass']),
                            'multi_az': db_instance.get('MultiAZ', False),
                            'read_replica_source': db_instance.get('ReadReplicaSourceDBInstanceIdentifier', ''),
                            'availability_zone': db_instance.get('AvailabilityZone', ''),
                        }
                        instances.append(instance_info)
                        
        except Exception as e:
            print(f"获取RDS实例失败: {e}")
            
        return instances

    def _determine_architecture(self, db_instance: Dict) -> str:
        """判断RDS实例的架构类型"""
        if db_instance.get('ReadReplicaSourceDBInstanceIdentifier'):
            return 'read_replica'
        elif db_instance.get('MultiAZ', False):
            return 'MAZ'
        else:
            return 'Non-MAZ'

    def get_all_ri_pricing(self) -> Dict[str, float]:
        """获取该region下所有MySQL实例类型的1年RI无预付价格"""
        ri_pricing_cache = {}
        
        try:
            print("正在获取RI定价...")
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'serviceCode', 'Value': 'AmazonRDS'},
                {'Type': 'TERM_MATCH', 'Field': 'databaseEngine', 'Value': 'MySQL'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name()},
                {'Type': 'TERM_MATCH', 'Field': 'deploymentOption', 'Value': 'Single-AZ'},
            ]
            
            paginator = self.pricing_client.get_paginator('get_products')
            page_iterator = paginator.paginate(
                ServiceCode='AmazonRDS',
                Filters=filters,
                MaxResults=100
            )
            
            for page in page_iterator:
                for product_str in page.get('PriceList', []):
                    product = json.loads(product_str)
                    attributes = product.get('product', {}).get('attributes', {})
                    instance_type = attributes.get('instanceType', '')
                    
                    if not instance_type:
                        continue
                    
                    reserved_terms = product.get('terms', {}).get('Reserved', {})
                    for term in reserved_terms.values():
                        term_attrs = term.get('termAttributes', {})
                        if (term_attrs.get('LeaseContractLength') == '1yr' and 
                            term_attrs.get('PurchaseOption') == 'No Upfront'):
                            
                            for price_dim in term.get('priceDimensions', {}).values():
                                if price_dim.get('unit') == 'Hrs':
                                    price = float(price_dim.get('pricePerUnit', {}).get('USD', 0))
                                    if price > 0:
                                        ri_pricing_cache[instance_type] = price
                                    break
                
            print(f"成功获取 {len(ri_pricing_cache)} 个实例类型的RI定价")
            
        except Exception as e:
            print(f"获取RI定价失败: {e}")

        return ri_pricing_cache

    def _get_location_name(self) -> str:
        """将AWS region转换为Pricing API使用的location名称"""
        region_mapping = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'eu-west-2': 'EU (London)',
            'eu-west-3': 'EU (Paris)',
            'eu-central-1': 'EU (Frankfurt)',
            'eu-central-2': 'Europe (Zurich)',
            'eu-north-1': 'EU (Stockholm)',
            'eu-south-1': 'EU (Milan)',
            'eu-south-2': 'Europe (Spain)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-southeast-2': 'Asia Pacific (Sydney)',
            'ap-southeast-3': 'Asia Pacific (Jakarta)',
            'ap-southeast-4': 'Asia Pacific (Melbourne)',
            'ap-southeast-5': 'Asia Pacific (Malaysia)',
            'ap-southeast-6': 'Asia Pacific (New Zealand)',
            'ap-southeast-7': 'Asia Pacific (Thailand)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            'ap-northeast-2': 'Asia Pacific (Seoul)',
            'ap-northeast-3': 'Asia Pacific (Osaka)',
            'ap-south-1': 'Asia Pacific (Mumbai)',
            'ap-south-2': 'Asia Pacific (Hyderabad)',
            'ap-east-1': 'Asia Pacific (Hong Kong)',
            'ap-east-2': 'Asia Pacific (Taipei)',
            'ca-central-1': 'Canada (Central)',
            'ca-west-1': 'Canada West (Calgary)',
            'sa-east-1': 'South America (Sao Paulo)',
            'af-south-1': 'Africa (Cape Town)',
            'me-central-1': 'Middle East (UAE)',
            'me-south-1': 'Middle East (Bahrain)',
            'il-central-1': 'Israel (Tel Aviv)',
            'mx-central-1': 'Mexico (Central)',
        }
        return region_mapping.get(self.region, 'US East (N. Virginia)')

    def calculate_mrr(self, hourly_rate) -> float:
        """计算月度经常性收入 (MRR)"""
        if hourly_rate == 'NA' or hourly_rate is None:
            return 'NA'
        try:
            return round(float(hourly_rate) * 730, 4)
        except (ValueError, TypeError):
            return 'NA'


    def _export_to_csv(self, results: List[Dict], output_file: str):
        """导出结果到CSV文件"""
        fieldnames = [
            'account_id', 'region', 'db_instance_identifier', 'mysql_engine_version', 
            'architecture', 'instance_class', 'cpu_cores',
            '1yr_ri_noupfront_hourly_rate_usd', '1yr_ri_noupfront_mrr_usd',
            'extended_support_year1_per_core_hourly_usd', 'extended_support_year1_mrr_usd',
            '1yr_extend_support vs. 1yr_ri_noupfront',
            'extended_support_year2_per_core_hourly_usd', 'extended_support_year2_mrr_usd',
            '2yr_extend_support vs. 1yr_ri_noupfront',
            'extended_support_year3_per_core_hourly_usd', 'extended_support_year3_mrr_usd',
            '3yr_extend_support vs. 1yr_ri_noupfront'
        ]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    def _export_to_csv(self, results: List[Dict]) -> str:
        """
        将分析结果导出为CSV格式的字符串
        
        Args:
            results: 分析结果列表
            
        Returns:
            CSV格式的字符串
        """
        if not results:
            return ""
        
        import io
        import csv
        
        fieldnames = [
            'account_id', 'region', 'db_instance_identifier', 'mysql_engine_version', 
            'architecture', 'instance_class', 'cpu_cores',
            '1yr_ri_noupfront_hourly_rate_usd', '1yr_ri_noupfront_mrr_usd',
            'extended_support_year1_per_core_hourly_usd', 'extended_support_year1_mrr_usd',
            '1yr_extend_support vs. 1yr_ri_noupfront',
            'extended_support_year2_per_core_hourly_usd', 'extended_support_year2_mrr_usd',
            '2yr_extend_support vs. 1yr_ri_noupfront',
            'extended_support_year3_per_core_hourly_usd', 'extended_support_year3_mrr_usd',
            '3yr_extend_support vs. 1yr_ri_noupfront'
        ]
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
        return output.getvalue()

    def analyze_and_export(self, output_format: str = "json") -> str:
        """
        分析RDS MySQL实例并返回结果，支持多种格式
        
        Args:
            output_format: 输出格式 ("json", "csv", "markdown")
            
        Returns:
            输出内容的字符串表示
        """
        print(f"开始分析 {self.region} 区域的RDS MySQL实例...")
        
        instances = self.get_rds_instances()
        print(f"找到 {len(instances)} 个MySQL实例")
        
        if not instances:
            print("未找到MySQL实例")
            return ""
        
        ri_pricing_cache = self.get_all_ri_pricing()
        
        results = []
        
        for instance in instances:
            print(f"分析实例: {instance['db_instance_identifier']}")
            
            ri_hourly_rate = ri_pricing_cache.get(instance['instance_class'], 0.0)
            
            # Multi-AZ实例RI费用乘以2
            multiplier = 2 if instance['architecture'] == 'MAZ' else 1
            adjusted_ri_hourly_rate = ri_hourly_rate * multiplier
            ri_mrr = self.calculate_mrr(adjusted_ri_hourly_rate)
            
            # 获取Extended Support定价
            extended_support_pricing = self.get_extended_support_pricing(instance['cpu_cores'])
            
            # 计算Extended Support MRR
            def calculate_extended_support_values(per_core_price, cpu_cores, multiplier):
                if per_core_price == 'NA':
                    return 'NA', 'NA'
                try:
                    total_hourly = float(per_core_price) * cpu_cores * multiplier
                    mrr = self.calculate_mrr(total_hourly)
                    return round(total_hourly, 4), mrr
                except (ValueError, TypeError):
                    return 'NA', 'NA'
            
            year1_total_hourly, year1_mrr = calculate_extended_support_values(
                extended_support_pricing['year1_per_core_per_hour'], instance['cpu_cores'], multiplier
            )
            year2_total_hourly, year2_mrr = calculate_extended_support_values(
                extended_support_pricing['year2_per_core_per_hour'], instance['cpu_cores'], multiplier
            )
            year3_total_hourly, year3_mrr = calculate_extended_support_values(
                extended_support_pricing['year3_per_core_per_hour'], instance['cpu_cores'], multiplier
            )
            
            # 计算比较百分比
            def calculate_percentage(es_mrr, ri_mrr):
                if es_mrr == 'NA' or ri_mrr == 'NA' or ri_mrr == 0:
                    return 'NA'
                try:
                    return f"{round(((es_mrr - ri_mrr) / ri_mrr) * 100, 3)}%"
                except (ValueError, TypeError, ZeroDivisionError):
                    return 'NA'
            
            ri_1yr_es_1yr = calculate_percentage(year1_mrr, ri_mrr) 
            ri_1yr_es_2yr = calculate_percentage(year2_mrr, ri_mrr) 
            ri_1yr_es_3yr = calculate_percentage(year3_mrr, ri_mrr) 

            result = {
                'account_id': instance['account_id'],
                'region': instance['region'],
                'db_instance_identifier': instance['db_instance_identifier'],
                'mysql_engine_version': instance['engine_version'],
                'architecture': instance['architecture'],
                'instance_class': instance['instance_class'],
                'cpu_cores': instance['cpu_cores'],
                '1yr_ri_noupfront_hourly_rate_usd': round(adjusted_ri_hourly_rate, 4),
                '1yr_ri_noupfront_mrr_usd': ri_mrr,
                'extended_support_year1_per_core_hourly_usd': extended_support_pricing['year1_per_core_per_hour'],
                'extended_support_year1_mrr_usd': year1_mrr,
                '1yr_extend_support vs. 1yr_ri_noupfront': ri_1yr_es_1yr,
                'extended_support_year2_per_core_hourly_usd': extended_support_pricing['year2_per_core_per_hour'],
                'extended_support_year2_mrr_usd': year2_mrr,
                '2yr_extend_support vs. 1yr_ri_noupfront': ri_1yr_es_2yr,
                'extended_support_year3_per_core_hourly_usd': extended_support_pricing['year3_per_core_per_hour'],
                'extended_support_year3_mrr_usd': year3_mrr,
                '3yr_extend_support vs. 1yr_ri_noupfront': ri_1yr_es_3yr
            }
            
            results.append(result)
        
        if not results:
            print("未找到MySQL实例或分析失败")
            return ""
        
        # 根据格式返回内容
        if output_format.lower() == "csv":
            return self._export_to_csv(results)
        elif output_format.lower() == "markdown":
            return self._export_to_markdown(results)
        else:  # JSON format
            return json.dumps(results, default=str, indent=2, ensure_ascii=False)

    def _export_to_markdown(self, results: List[Dict]) -> str:
        """
        将分析结果导出为Markdown格式
        
        Args:
            results: 分析结果列表
            
        Returns:
            Markdown格式的字符串
        """
        if not results:
            return "# RDS MySQL Extended Support Pricing Analysis\n\n没有找到数据。"
        
        md_content = []
        md_content.append("# RDS MySQL Extended Support Pricing Analysis")
        md_content.append(f"\n**分析区域**: {self.region}")
        md_content.append(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_content.append(f"**实例数量**: {len(results)}")
        
        # 汇总表格
        md_content.append("\n## 实例汇总")
        md_content.append("\n| 实例标识符 | 实例类型 | CPU核心数 | 架构 | 1年RI MRR | 扩展支持1年MRR | 扩展支持2年MRR | 扩展支持3年MRR |")
        md_content.append("|---|---|---|---|---|---|---|---|")
        
        for result in results:
            db_id = result.get('db_instance_identifier', 'N/A')
            instance_class = result.get('instance_class', 'N/A')
            cpu_cores = result.get('cpu_cores', 0)
            architecture = result.get('architecture', 'N/A')
            ri_mrr = result.get('1yr_ri_noupfront_mrr_usd', 'N/A')
            year1_mrr = result.get('extended_support_year1_mrr_usd', 'N/A')
            year2_mrr = result.get('extended_support_year2_mrr_usd', 'N/A')
            year3_mrr = result.get('extended_support_year3_mrr_usd', 'N/A')
            
            md_content.append(f"| {db_id} | {instance_class} | {cpu_cores} | {architecture} | ${ri_mrr} | ${year1_mrr} | ${year2_mrr} | ${year3_mrr} |")
        
        # 详细实例信息
        md_content.append("\n## 详细实例分析")
        
        for i, result in enumerate(results, 1):
            md_content.append(f"\n### {i}. {result.get('db_instance_identifier', 'Unknown')}")
            
            # 基本信息
            md_content.append("\n#### 基本信息")
            md_content.append(f"- **账户ID**: {result.get('account_id', 'N/A')}")
            md_content.append(f"- **区域**: {result.get('region', 'N/A')}")
            md_content.append(f"- **MySQL版本**: {result.get('mysql_engine_version', 'N/A')}")
            md_content.append(f"- **架构**: {result.get('architecture', 'N/A')}")
            md_content.append(f"- **实例类型**: {result.get('instance_class', 'N/A')}")
            md_content.append(f"- **CPU核心数**: {result.get('cpu_cores', 0)}")
            
            # 成本分析
            md_content.append("\n#### 成本分析")
            md_content.append(f"- **1年RI MRR**: ${result.get('1yr_ri_noupfront_mrr_usd', 'N/A')}")
            md_content.append(f"- **扩展支持1年MRR**: ${result.get('extended_support_year1_mrr_usd', 'N/A')}")
            md_content.append(f"- **扩展支持2年MRR**: ${result.get('extended_support_year2_mrr_usd', 'N/A')}")
            md_content.append(f"- **扩展支持3年MRR**: ${result.get('extended_support_year3_mrr_usd', 'N/A')}")
            
            # 成本比较
            md_content.append("\n#### 成本比较")
            md_content.append(f"- **1年扩展支持 vs 1年RI**: {result.get('1yr_extend_support vs. 1yr_ri_noupfront', 'N/A')}")
            md_content.append(f"- **2年扩展支持 vs 1年RI**: {result.get('2yr_extend_support vs. 1yr_ri_noupfront', 'N/A')}")
            md_content.append(f"- **3年扩展支持 vs 1年RI**: {result.get('3yr_extend_support vs. 1yr_ri_noupfront', 'N/A')}")
        
        return '\n'.join(md_content)

def main():
    parser = argparse.ArgumentParser(description='RDS MySQL实例定价分析工具 - API版本')
    parser.add_argument('region', help='AWS区域名称 (例如: us-east-1)')
    parser.add_argument('-o', '--output', help='输出CSV文件名称')
    
    args = parser.parse_args()
    
    try:
        analyzer = RDSPricingAnalyzer(args.region)
        analyzer.analyze_and_export(args.output)
    except Exception as e:
        print(f"脚本执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

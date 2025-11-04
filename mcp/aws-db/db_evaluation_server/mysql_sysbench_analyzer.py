#!/usr/bin/env python3
"""
MySQL Sysbench Performance Testing Analyzer
Provides sysbench performance testing capabilities for MySQL clusters
"""

import subprocess
import time
import logging
import json
import csv
import io
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

# Initialize logger
logger = logging.getLogger(__name__)

@dataclass
class MySQLClusterConfig:
    """MySQL cluster configuration for sysbench testing"""
    endpoint: str
    port: int = 3306
    username: str = "admin"
    password: str = ""
    database: str = "sysbench_test"
    version: str = ""
    instance_size: str = ""

@dataclass
class SysbenchTestConfig:
    """Sysbench test configuration"""
    table_count: int = 100
    table_size: int = 35000000
    test_duration: int = 300  # seconds
    scenarios: List[str] = None
    thread_counts: List[int] = None
    
    def __post_init__(self):
        if self.scenarios is None:
            self.scenarios = ['oltp_read_write']
        if self.thread_counts is None:
            self.thread_counts = [128, 256, 512]

@dataclass
class SysbenchResult:
    """Sysbench test result"""
    cluster_version: str
    cluster_size: str
    scenario: str
    threads: int
    qps: int
    tps: int
    latency_95th: float
    test_duration: int
    timestamp: str

class MySQLSysbenchAnalyzer:
    """MySQL Sysbench Performance Testing Analyzer"""
    
    def __init__(self):
        self.results: List[SysbenchResult] = []
    
    def check_sysbench_available(self) -> bool:
        """Check if sysbench is available in the system"""
        try:
            result = subprocess.run(['sysbench', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def check_mysql_connection(self, cluster: MySQLClusterConfig) -> bool:
        """Check MySQL connection"""
        try:
            cmd = [
                'mysql',
                f'-h{cluster.endpoint}',
                f'-P{cluster.port}',
                f'-u{cluster.username}',
                f'-p{cluster.password}',
                '-e', 'SELECT 1;'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result.returncode == 0 and 'ERROR' not in result.stderr
        except subprocess.TimeoutExpired:
            return False
    
    def prepare_database(self, cluster: MySQLClusterConfig) -> bool:
        """Prepare database for sysbench testing"""
        try:
            # Drop and create database
            cmd = [
                'mysql',
                f'-h{cluster.endpoint}',
                f'-P{cluster.port}',
                f'-u{cluster.username}',
                f'-p{cluster.password}',
                '-e', f'DROP DATABASE IF EXISTS {cluster.database}; CREATE DATABASE {cluster.database};'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                logger.error(f"Failed to create database: {result.stderr}")
                return False
            
            logger.info(f"Database {cluster.database} created successfully")
            return True
        except subprocess.TimeoutExpired:
            logger.error("Database creation timed out")
            return False
    
    def prepare_test_data(self, cluster: MySQLClusterConfig, config: SysbenchTestConfig) -> bool:
        """Prepare test data using sysbench"""
        try:
            cmd = [
                'sysbench',
                f'--mysql-host={cluster.endpoint}',
                f'--mysql-port={cluster.port}',
                f'--mysql-db={cluster.database}',
                f'--mysql-user={cluster.username}',
                f'--mysql-password={cluster.password}',
                f'--table_size={config.table_size}',
                f'--tables={config.table_count}',
                '--threads=128',
                'oltp_read_write',
                'prepare'
            ]
            
            logger.info(f"Preparing test data for {cluster.endpoint}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hour timeout
            
            if result.returncode != 0:
                logger.error(f"Failed to prepare test data: {result.stderr}")
                return False
            
            logger.info("Test data prepared successfully")
            return True
        except subprocess.TimeoutExpired:
            logger.error("Test data preparation timed out")
            return False
    
    def run_sysbench_test(self, cluster: MySQLClusterConfig, config: SysbenchTestConfig, 
                         scenario: str, threads: int) -> Optional[SysbenchResult]:
        """Run a single sysbench test"""
        try:
            cmd = [
                'sysbench',
                f'--mysql-host={cluster.endpoint}',
                f'--mysql-port={cluster.port}',
                f'--mysql-db={cluster.database}',
                f'--mysql-user={cluster.username}',
                f'--mysql-password={cluster.password}',
                f'--table_size={config.table_size}',
                f'--tables={config.table_count}',
                f'--threads={threads}',
                f'--time={config.test_duration}',
                '--percentile=95',
                '--auto_inc=on',
                '--mysql-ignore-errors=1062,1213',
                '--skip-trx=1',
                scenario,
                'run'
            ]
            
            logger.info(f"Running test: {cluster.version} | {cluster.instance_size} | {scenario} | {threads} threads")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=config.test_duration + 120)
            
            if result.returncode != 0:
                logger.error(f"Sysbench test failed: {result.stdout}")
                return None
            
            # Parse results
            output = result.stdout
            tps = self._extract_tps(output)
            qps = self._extract_qps(output)
            latency_95th = self._extract_latency_95th(output)
            
            return SysbenchResult(
                cluster_version=cluster.version,
                cluster_size=cluster.instance_size,
                scenario=scenario,
                threads=threads,
                qps=qps,
                tps=tps,
                latency_95th=latency_95th,
                test_duration=config.test_duration,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Sysbench test timed out for {threads} threads")
            return None
    
    def _extract_tps(self, output: str) -> int:
        """Extract TPS from sysbench output"""
        pattern = r'transactions:\s+\d+\s+\((\d+(?:\.\d+)?)\s+per sec\.\)'
        match = re.search(pattern, output)
        return int(float(match.group(1))) if match else 0
    
    def _extract_qps(self, output: str) -> int:
        """Extract QPS from sysbench output"""
        pattern = r'queries:\s+\d+\s+\((\d+(?:\.\d+)?)\s+per sec\.\)'
        match = re.search(pattern, output)
        return int(float(match.group(1))) if match else 0
    
    def _extract_latency_95th(self, output: str) -> float:
        """Extract 95th percentile latency from sysbench output"""
        pattern = r'95th percentile:\s+(\d+(?:\.\d+)?)'
        match = re.search(pattern, output)
        return float(match.group(1)) if match else 0.0
    
    def run_performance_tests(self, clusters: List[MySQLClusterConfig], 
                            config: SysbenchTestConfig) -> List[SysbenchResult]:
        """Run performance tests on multiple clusters"""
        self.results = []
        
        # Check if sysbench is available
        if not self.check_sysbench_available():
            raise RuntimeError("Sysbench is not available. Please install sysbench first.")
        
        for cluster in clusters:
            logger.info(f"Testing cluster: {cluster.endpoint}")
            
            # Check connection
            if not self.check_mysql_connection(cluster):
                logger.error(f"Cannot connect to MySQL cluster: {cluster.endpoint}")
                continue
            
            # Prepare database and data
            if not self.prepare_database(cluster):
                logger.error(f"Failed to prepare database for cluster: {cluster.endpoint}")
                continue
            
            if not self.prepare_test_data(cluster, config):
                logger.error(f"Failed to prepare test data for cluster: {cluster.endpoint}")
                continue
            
            # Run tests for each scenario and thread count
            for scenario in config.scenarios:
                for threads in config.thread_counts:
                    result = self.run_sysbench_test(cluster, config, scenario, threads)
                    if result:
                        self.results.append(result)
                    
                    # Wait between tests
                    time.sleep(6)
        
        return self.results
    
    def export_to_csv(self) -> str:
        """Export results to CSV format"""
        if not self.results:
            return "No test results available"
        
        output = io.StringIO()
        
        # Group results by scenario for better formatting
        scenarios = list(set(result.scenario for result in self.results))
        thread_counts = sorted(list(set(result.threads for result in self.results)))
        
        # Write header
        header = ['Version', 'Size', 'Scenario', 'Metrics']
        for threads in thread_counts:
            header.append(f'thread-{threads}')
        
        writer = csv.writer(output)
        writer.writerow(header)
        
        # Group results by cluster and scenario
        cluster_scenarios = {}
        for result in self.results:
            key = (result.cluster_version, result.cluster_size, result.scenario)
            if key not in cluster_scenarios:
                cluster_scenarios[key] = {}
            cluster_scenarios[key][result.threads] = result
        
        # Write data rows
        for (version, size, scenario), thread_results in cluster_scenarios.items():
            # QPS row
            qps_row = [version, size, scenario, 'QPS']
            for threads in thread_counts:
                qps = thread_results.get(threads, SysbenchResult('', '', '', 0, 0, 0, 0, 0, '')).qps
                qps_row.append(qps)
            writer.writerow(qps_row)
            
            # TPS row
            tps_row = [version, size, scenario, 'TPS']
            for threads in thread_counts:
                tps = thread_results.get(threads, SysbenchResult('', '', '', 0, 0, 0, 0, 0, '')).tps
                tps_row.append(tps)
            writer.writerow(tps_row)
            
            # Latency row
            latency_row = [version, size, scenario, 'Latency/ms']
            for threads in thread_counts:
                latency = thread_results.get(threads, SysbenchResult('', '', '', 0, 0, 0, 0, 0, '')).latency_95th
                latency_row.append(latency)
            writer.writerow(latency_row)
        
        return output.getvalue()
    
    def export_to_markdown(self) -> str:
        """Export results to Markdown format"""
        if not self.results:
            return "No test results available"
        
        markdown = "# MySQL Sysbench Performance Test Results\n\n"
        markdown += f"**Test Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Group results by cluster and scenario
        cluster_scenarios = {}
        for result in self.results:
            key = (result.cluster_version, result.cluster_size, result.scenario)
            if key not in cluster_scenarios:
                cluster_scenarios[key] = []
            cluster_scenarios[key].append(result)
        
        for (version, size, scenario), results in cluster_scenarios.items():
            markdown += f"## {version} - {size} - {scenario}\n\n"
            
            # Create table
            markdown += "| Threads | QPS | TPS | 95th Percentile Latency (ms) |\n"
            markdown += "|---------|-----|-----|------------------------------|\n"
            
            # Sort results by thread count
            results.sort(key=lambda x: x.threads)
            
            for result in results:
                markdown += f"| {result.threads} | {result.qps} | {result.tps} | {result.latency_95th} |\n"
            
            markdown += "\n"
        
        # Add summary statistics
        if self.results:
            markdown += "## Summary Statistics\n\n"
            max_qps = max(result.qps for result in self.results)
            max_tps = max(result.tps for result in self.results)
            min_latency = min(
                (result.latency_95th for result in self.results if result.latency_95th > 0),
                default=None
            )
            
            markdown += f"- **Maximum QPS:** {max_qps}\n"
            markdown += f"- **Maximum TPS:** {max_tps}\n"
            markdown += f"- **Minimum 95th Percentile Latency:** {min_latency} ms\n"
            markdown += f"- **Total Tests Completed:** {len(self.results)}\n"
        
        return markdown
    
    def export_to_json(self) -> str:
        """Export results to JSON format"""
        if not self.results:
            return json.dumps({"message": "No test results available"}, indent=2)
        
        results_dict = {
            "test_metadata": {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "total_tests": len(self.results)
            },
            "results": []
        }
        
        for result in self.results:
            results_dict["results"].append({
                "cluster_version": result.cluster_version,
                "cluster_size": result.cluster_size,
                "scenario": result.scenario,
                "threads": result.threads,
                "qps": result.qps,
                "tps": result.tps,
                "latency_95th_ms": result.latency_95th,
                "test_duration_seconds": result.test_duration,
                "timestamp": result.timestamp
            })
        
        return json.dumps(results_dict, indent=2)

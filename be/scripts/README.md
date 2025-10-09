# ChatRecordTable 迁移脚本

本目录包含用于将ChatRecordTable从旧结构迁移到新结构的脚本集合。

## 背景

原来的ChatRecordTable使用`id`作为partition key，现在需要改为使用`user_id`作为partition key，`id`作为sort key，以支持按用户查询和编排执行记录的统一存储。

## 脚本说明

### 1. `export_chat_records.py` - 数据导出脚本
- **功能**: 导出现有ChatRecordTable和ChatResponseTable中的所有数据
- **输出**: 生成带时间戳的JSON备份文件 `chat_records_backup_YYYYMMDD_HHMMSS.json`
- **特性**: 
  - 自动处理user_id为空的记录（设置为'public'）
  - 包含完整的统计信息
  - 支持大表的分页扫描

### 2. `rebuild_chat_tables.py` - 表重建脚本
- **功能**: 删除旧表并创建新的表结构
- **新结构**: 
  - ChatRecordTable: partition_key=user_id, sort_key=id
  - ChatResponseTable: partition_key=id, sort_key=resp_no (保持不变)
- **安全性**: 需要输入'YES'确认操作

### 3. `import_chat_records.py` - 数据导入脚本
- **功能**: 将备份的JSON数据导入到新表结构中
- **特性**:
  - 自动查找最新的备份文件
  - 支持指定备份文件路径
  - 包含导入验证和统计

### 4. `migrate_chat_tables.py` - 完整迁移脚本
- **功能**: 一键执行完整的迁移流程
- **流程**: 导出 → 重建表 → 导入数据
- **优势**: 自动化整个过程，减少人工错误

## 使用方法

### 方法一：一键迁移（推荐）

```bash
cd be/scripts
python migrate_chat_tables.py
```

### 方法二：分步执行

```bash
cd be/scripts

# 步骤1: 导出数据
python export_chat_records.py

# 步骤2: 重建表结构
python rebuild_chat_tables.py

# 步骤3: 导入数据
python import_chat_records.py
```

### 方法三：指定备份文件导入

```bash
cd be/scripts
python import_chat_records.py chat_records_backup_20251003_143000.json
```

## 注意事项

### ⚠️ 重要警告
- **数据安全**: 迁移过程会删除原表，请确保在生产环境中谨慎操作
- **服务停机**: 迁移期间ChatRecord相关功能将不可用
- **权限要求**: 需要DynamoDB的创建、删除、读写权限

### 📋 迁移前检查清单
- [ ] 确认没有其他程序正在使用ChatRecordTable
- [ ] 确认AWS凭证和权限配置正确
- [ ] 确认有足够的磁盘空间存储备份文件
- [ ] 通知相关用户服务将暂时不可用

### 🔍 迁移后验证
- [ ] 检查新表结构是否正确
- [ ] 验证数据完整性
- [ ] 测试应用功能是否正常
- [ ] 确认用户数据按user_id正确分区

## 表结构对比

### 旧结构
```
ChatRecordTable:
- Partition Key: id (String)
- 查询方式: 只能通过id查询单条记录
```

### 新结构
```
ChatRecordTable:
- Partition Key: user_id (String)
- Sort Key: id (String)
- 查询方式: 
  - 按user_id查询用户所有记录
  - 按user_id + id查询特定记录
```

## 故障排除

### 常见问题

1. **权限错误**
   ```
   解决方案: 检查AWS凭证和DynamoDB权限
   ```

2. **表不存在**
   ```
   解决方案: 确认表名配置正确，检查AWS区域设置
   ```

3. **导入失败**
   ```
   解决方案: 检查备份文件格式，确认新表结构正确
   ```

4. **数据丢失**
   ```
   解决方案: 检查备份文件，重新运行导入脚本
   ```

### 日志和调试
- 所有脚本都包含详细的进度输出
- 错误信息会显示具体的失败原因
- 可以通过返回码判断脚本执行状态

## 回滚方案

如果迁移失败，可以通过以下步骤回滚：

1. **保留备份文件**: 不要删除生成的JSON备份文件
2. **重建旧表结构**: 手动创建原来的表结构
3. **导入备份数据**: 修改导入脚本以适配旧结构

## 性能考虑

- **导出时间**: 取决于数据量，通常每万条记录需要几秒钟
- **表重建时间**: DynamoDB表删除和创建通常需要几分钟
- **导入时间**: 取决于数据量和网络状况

## 支持

如果遇到问题，请检查：
1. AWS凭证配置
2. 网络连接
3. DynamoDB权限
4. 脚本输出的错误信息

---

**最后更新**: 2025-10-03
**版本**: 1.0.0

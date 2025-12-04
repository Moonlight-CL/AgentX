-- PostgreSQL DDL for edu_ref_docs table
-- 需要先启用 pgvector 扩展来支持向量字段
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建 edu_ref_docs 表
CREATE TABLE edu_ref_docs (
    id SERIAL PRIMARY KEY,
    doc_category VARCHAR(32) NOT NULL, -- 文档类别
    doc_title VARCHAR(255) NOT NULL, -- 文档标题
    content TEXT NOT NULL, -- 文档内容
    content_vector vector(1024), -- 内容向量，使用1024维度（适配Cohere embeddings）
    summary TEXT, -- 文档摘要
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 添加表和列的注释
COMMENT ON TABLE edu_ref_docs IS '教育参考文档表';
COMMENT ON COLUMN edu_ref_docs.id IS '主键ID';
COMMENT ON COLUMN edu_ref_docs.doc_category IS '文档类别';
COMMENT ON COLUMN edu_ref_docs.doc_title IS '文档标题';
COMMENT ON COLUMN edu_ref_docs.content IS '文档内容';
COMMENT ON COLUMN edu_ref_docs.content_vector IS '内容向量，使用1024维度（适配Cohere embeddings）';
COMMENT ON COLUMN edu_ref_docs.summary IS '文档摘要';
COMMENT ON COLUMN edu_ref_docs.created_at IS '创建时间';
COMMENT ON COLUMN edu_ref_docs.updated_at IS '更新时间';

-- 创建索引以提高查询性能
CREATE INDEX idx_edu_ref_docs_category ON edu_ref_docs(doc_category);
CREATE INDEX idx_edu_ref_docs_created_at ON edu_ref_docs(created_at);

-- 为向量字段创建ivfflat索引以支持相似性搜索
-- 注意：需要表中有数据后才能创建此索引
-- CREATE INDEX idx_edu_ref_docs_content_vector ON edu_ref_docs 
-- USING ivfflat (content_vector vector_cosine_ops) WITH (lists = 100);
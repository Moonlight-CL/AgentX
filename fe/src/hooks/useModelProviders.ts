import { useState, useEffect } from 'react';
import { configAPI } from '../services/api';
import type { SystemConfig } from '../services/api';

export interface ModelProvider {
  key: string;
  displayName: string;
  val: number;
  models: ModelConfig[];
}

export interface ModelConfig {
  id: string;
  displayName: string;
  config: {
    model_id: string;
    temperature?: number;
    top_p?: number;
    max_tokens?: number;
    api_base_url?: string;
    api_key?: string;
  };
}

export const useModelProviders = () => {
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadModelProviders = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取 model_providers 分类下的所有配置
      const response = await configAPI.getConfigsByParent('model_providers');
      const configs = response.data;

      // 按提供商分组
      const providerMap = new Map<string, ModelProvider>();

      configs.forEach((config: SystemConfig) => {
        if (config.type === 'category' && config.parent === 'model_providers') {
          // 这是一个提供商分类
          const providerKey = config.key.replace('model_providers.', '');
          const val = JSON.parse(config.value)["val"];

          if (!providerMap.has(providerKey)) {
            providerMap.set(providerKey, {
              key: providerKey,
              val: val,
              displayName: config.key_display_name || providerKey,
              models: []
            });
          }
        }
      });

      // 获取每个提供商下的模型配置
      for (const [providerKey, provider] of providerMap.entries()) {
        try {
          const modelsResponse = await configAPI.getConfigsByParent(providerKey);
          const modelConfigs = modelsResponse.data;

          provider.models = modelConfigs
            .filter((config: SystemConfig) => config.type === 'item')
            .map((config: SystemConfig) => {
              try {
                const parsedConfig = JSON.parse(config.value);
                return {
                  id: config.key,
                  displayName: config.key_display_name || config.key.split('.').pop() || config.key,
                  config: parsedConfig
                };
              } catch (e) {
                console.error(`Error parsing config for ${config.key}:`, e);
                return null;
              }
            })
            .filter(Boolean) as ModelConfig[];
        } catch (e) {
          console.error(`Error loading models for provider ${providerKey}:`, e);
        }
      }

      setProviders(Array.from(providerMap.values()));
    } catch (err) {
      console.error('Error loading model providers:', err);
      setError(err instanceof Error ? err.message : 'Failed to load model providers');
      
      // 如果配置加载失败，使用默认的硬编码配置作为后备
      setProviders(getDefaultProviders());
    } finally {
      setLoading(false);
    }
  };

  // 默认的硬编码配置作为后备
  const getDefaultProviders = (): ModelProvider[] => [
    {
      key: 'Bedrock',
      displayName: 'Amazon Bedrock',
      val: 1,
      models: [
        {
          id: 'claude-opus',
          displayName: 'Claude Opus',
          config: {
            model_id: 'us.anthropic.claude-opus-4-20250514-v1:0',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096
          }
        },
        {
          id: 'claude-sonnet',
          displayName: 'Claude Sonnet',
          config: {
            model_id: 'us.anthropic.claude-sonnet-4-20250514-v1:0',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096
          }
        },
        {
          id: 'claude-3-7-sonnet',
          displayName: 'Claude 3.7 Sonnet',
          config: {
            model_id: 'us.anthropic.claude-3-7-sonnet-20250219-v1:0',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096
          }
        }
      ]
    },
    {
      key: 'OpenAI',
      displayName: 'OpenAI',
      val: 2,
      models: [
        {
          id: 'gpt-4',
          displayName: 'GPT-4',
          config: {
            model_id: 'gpt-4',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096,
            api_base_url: 'https://api.openai.com/v1',
            api_key: ''
          }
        },
        {
          id: 'gpt-4-turbo',
          displayName: 'GPT-4 Turbo',
          config: {
            model_id: 'gpt-4-turbo',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096,
            api_base_url: 'https://api.openai.com/v1',
            api_key: ''
          }
        },
        {
          id: 'gpt-4o',
          displayName: 'GPT-4o',
          config: {
            model_id: 'gpt-4o',
            temperature: 0.7,
            top_p: 1.0,
            max_tokens: 4096,
            api_base_url: 'https://api.openai.com/v1',
            api_key: ''
          }
        }
      ]
    }
  ];

  // 根据提供商key获取提供商信息
  const getProvider = (providerKey: string): ModelProvider | undefined => {
    return providers.find(p => p.key === providerKey);
  };

  // 根据提供商key和模型id获取模型配置
  const getModelConfig = (providerKey: string, modelId: string): ModelConfig | undefined => {
    const provider = getProvider(providerKey);
    return provider?.models.find(m => m.config.model_id === modelId);
  };

  // 获取所有提供商的key列表
  const getProviderKeys = (): string[] => {
    return providers.map(p => p.key);
  };

  // 获取指定提供商的所有模型ID列表
  const getModelIds = (providerKey: string): string[] => {
    const provider = getProvider(providerKey);
    return provider?.models.map(m => m.config.model_id) || [];
  };

  // 将新的配置格式转换为旧的数字格式（用于向后兼容）
  const getProviderNumber = (providerKey: string): number => {
    
    const provider = getProvider(providerKey);
    return provider?.val || 1000;

    // const providerMap: Record<string, number> = {
    //   'Bedrock': 1,
    //   'OpenAI': 2,
    //   'Anthropic': 3,
    //   'LiteLLM': 4,
    //   'Ollama': 5,
    //   'Custom': 6
    // };
    // return providerMap[providerKey] || 6; // 默认为 custom
  };

  // 将数字格式转换为新的key格式（用于向后兼容）
  const getProviderKey = (providerNumber: number): string => {

    const result = providers.find(p => p.val === providerNumber)?.key || "Custome";
    return result;

    // const numberMap: Record<number, string> = {
    //   1: 'Bedrock',
    //   2: 'OpenAI',
    //   3: 'Anthropic',
    //   4: 'LiteLLM',
    //   5: 'Ollama',
    //   6: 'Custom'
    // };
    // return numberMap[providerNumber] || 'custom';
  };

  useEffect(() => {
    loadModelProviders();
  }, []);

  return {
    providers,
    loading,
    error,
    reload: loadModelProviders,
    getProvider,
    getModelConfig,
    getProviderKeys,
    getModelIds,
    getProviderNumber,
    getProviderKey
  };
};

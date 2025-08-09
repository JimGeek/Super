import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Zap, Globe, Database, Code, Webhook, MessageSquare } from 'lucide-react';

interface ActionNodeData {
  label: string;
  actionType: 'http_request' | 'database' | 'transform' | 'webhook' | 'custom_code' | 'api_call';
  description?: string;
  config?: {
    method?: string;
    url?: string;
    headers?: Record<string, string>;
    body?: string;
    timeout?: number;
  };
}

const actionIcons = {
  http_request: Globe,
  database: Database,
  transform: Code,
  webhook: Webhook,
  custom_code: Code,
  api_call: MessageSquare,
};

const ActionNode: React.FC<NodeProps<ActionNodeData>> = ({ data, selected }) => {
  const Icon = actionIcons[data.actionType] || Zap;
  
  return (
    <Card className={`min-w-56 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-blue-200 hover:border-blue-300'
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-blue-400 bg-white"
        />
        
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Icon className="w-5 h-5 text-blue-600" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Action'}
            </h3>
            
            <Badge variant="outline" className="mt-1 text-xs">
              {data.actionType.replace('_', ' ')}
            </Badge>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-2">
                {data.description}
              </p>
            )}
            
            {/* Show configuration preview */}
            {data.config && (
              <div className="mt-2 space-y-1">
                {data.config.method && (
                  <div className="flex items-center space-x-2 text-xs">
                    <Badge variant="secondary" className="text-xs px-1 py-0">
                      {data.config.method}
                    </Badge>
                    {data.config.url && (
                      <span className="text-gray-500 truncate">
                        {data.config.url}
                      </span>
                    )}
                  </div>
                )}
                
                {data.config.timeout && (
                  <div className="text-xs text-gray-500">
                    Timeout: {data.config.timeout}ms
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 border-2 border-blue-400 bg-white"
        />
      </CardContent>
    </Card>
  );
};

export default ActionNode;
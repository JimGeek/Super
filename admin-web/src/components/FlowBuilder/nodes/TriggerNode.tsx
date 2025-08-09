import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Zap, Webhook, Clock, Bell, Calendar, Database } from 'lucide-react';

interface TriggerNodeData {
  label: string;
  triggerType: 'webhook' | 'schedule' | 'event' | 'database' | 'api' | 'manual';
  description?: string;
  config: {
    url?: string;
    method?: string;
    cronExpression?: string;
    eventType?: string;
    apiEndpoint?: string;
    schedule?: string;
  };
}

const triggerIcons = {
  webhook: Webhook,
  schedule: Clock,
  event: Bell,
  database: Database,
  api: Zap,
  manual: Calendar,
};

const triggerColors = {
  webhook: 'bg-orange-100 text-orange-600',
  schedule: 'bg-blue-100 text-blue-600',
  event: 'bg-purple-100 text-purple-600',
  database: 'bg-green-100 text-green-600',
  api: 'bg-red-100 text-red-600',
  manual: 'bg-gray-100 text-gray-600',
};

const TriggerNode: React.FC<NodeProps<TriggerNodeData>> = ({ data, selected }) => {
  const Icon = triggerIcons[data.triggerType] || Zap;
  const colorClass = triggerColors[data.triggerType] || 'bg-gray-100 text-gray-600';
  
  return (
    <Card className={`min-w-60 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-orange-200 hover:border-orange-300'
    }`}>
      <CardContent className="p-3">
        <div className="flex items-start space-x-3 mb-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Trigger'}
            </h3>
            
            <Badge variant="outline" className="mt-1 text-xs">
              {data.triggerType.toUpperCase()}
            </Badge>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-2">
                {data.description}
              </p>
            )}
          </div>
        </div>
        
        {/* Configuration Preview */}
        {data.config && (
          <div className="space-y-2">
            {/* Webhook Configuration */}
            {data.triggerType === 'webhook' && (
              <div className="space-y-1">
                {data.config.url && (
                  <div className="text-xs">
                    <span className="text-gray-500">URL:</span>
                    <div className="mt-1 bg-orange-50 rounded px-2 py-1 font-mono text-orange-700 truncate">
                      {data.config.url}
                    </div>
                  </div>
                )}
                
                {data.config.method && (
                  <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">Method:</span>
                    <Badge variant="secondary" className="text-xs">
                      {data.config.method}
                    </Badge>
                  </div>
                )}
              </div>
            )}
            
            {/* Schedule Configuration */}
            {data.triggerType === 'schedule' && (
              <div className="space-y-1">
                {data.config.cronExpression && (
                  <div className="text-xs">
                    <span className="text-gray-500">Cron:</span>
                    <div className="mt-1 bg-blue-50 rounded px-2 py-1 font-mono text-blue-700">
                      {data.config.cronExpression}
                    </div>
                  </div>
                )}
                
                {data.config.schedule && (
                  <div className="text-xs">
                    <span className="text-gray-500">Schedule:</span>
                    <div className="mt-1 text-blue-600 font-medium">
                      {data.config.schedule}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Event Configuration */}
            {data.triggerType === 'event' && data.config.eventType && (
              <div className="text-xs">
                <span className="text-gray-500">Event Type:</span>
                <Badge variant="secondary" className="ml-2 text-xs">
                  {data.config.eventType}
                </Badge>
              </div>
            )}
            
            {/* API Configuration */}
            {data.triggerType === 'api' && data.config.apiEndpoint && (
              <div className="text-xs">
                <span className="text-gray-500">Endpoint:</span>
                <div className="mt-1 bg-red-50 rounded px-2 py-1 font-mono text-red-700 truncate">
                  {data.config.apiEndpoint}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Trigger Status Indicator */}
        <div className="mt-3 pt-2 border-t border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-xs text-green-600 font-medium">Active</span>
            </div>
            <div className="text-xs text-gray-500">
              Last: 2m ago
            </div>
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 border-2 border-orange-400 bg-white"
        />
      </CardContent>
    </Card>
  );
};

export default TriggerNode;
import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Bell, MessageSquare, Mail, Smartphone, Push } from 'lucide-react';

interface NotificationNodeData {
  label: string;
  notificationType: 'sms' | 'email' | 'push' | 'whatsapp' | 'webhook';
  description?: string;
  config: {
    template?: string;
    recipients?: string[];
    subject?: string;
    priority?: 'low' | 'normal' | 'high';
  };
}

const notificationIcons = {
  sms: MessageSquare,
  email: Mail,
  push: Bell,
  whatsapp: Smartphone,
  webhook: Push,
};

const notificationColors = {
  sms: 'bg-green-100 text-green-600',
  email: 'bg-blue-100 text-blue-600',
  push: 'bg-purple-100 text-purple-600',
  whatsapp: 'bg-green-100 text-green-600',
  webhook: 'bg-orange-100 text-orange-600',
};

const NotificationNode: React.FC<NodeProps<NotificationNodeData>> = ({ data, selected }) => {
  const Icon = notificationIcons[data.notificationType] || Bell;
  const colorClass = notificationColors[data.notificationType] || 'bg-gray-100 text-gray-600';
  
  return (
    <Card className={`min-w-60 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-cyan-200 hover:border-cyan-300'
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-cyan-400 bg-white"
        />
        
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Notification'}
            </h3>
            
            <Badge variant="outline" className="mt-1 text-xs">
              {data.notificationType.toUpperCase()}
            </Badge>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-2">
                {data.description}
              </p>
            )}
            
            {/* Configuration Preview */}
            {data.config && (
              <div className="mt-2 space-y-1">
                {data.config.subject && (
                  <div className="text-xs">
                    <span className="text-gray-500">Subject:</span>
                    <span className="ml-1 font-medium truncate block">
                      {data.config.subject}
                    </span>
                  </div>
                )}
                
                {data.config.template && (
                  <div className="text-xs">
                    <span className="text-gray-500">Template:</span>
                    <div className="mt-1 bg-gray-50 rounded px-2 py-1 text-xs font-mono truncate">
                      {data.config.template}
                    </div>
                  </div>
                )}
                
                {data.config.recipients && data.config.recipients.length > 0 && (
                  <div className="text-xs">
                    <span className="text-gray-500">Recipients:</span>
                    <span className="ml-1">{data.config.recipients.length}</span>
                  </div>
                )}
                
                {data.config.priority && data.config.priority !== 'normal' && (
                  <Badge 
                    variant={data.config.priority === 'high' ? 'destructive' : 'secondary'} 
                    className="text-xs"
                  >
                    {data.config.priority} priority
                  </Badge>
                )}
              </div>
            )}
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 border-2 border-cyan-400 bg-white"
        />
      </CardContent>
    </Card>
  );
};

export default NotificationNode;
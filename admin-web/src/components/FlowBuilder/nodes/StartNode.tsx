import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Play } from 'lucide-react';

interface StartNodeData {
  label: string;
  description?: string;
  triggerType?: 'manual' | 'webhook' | 'schedule' | 'event';
}

const StartNode: React.FC<NodeProps<StartNodeData>> = ({ data, selected }) => {
  return (
    <Card className={`min-w-48 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-green-200 hover:border-green-300'
    }`}>
      <CardContent className="p-3">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
              <Play className="w-5 h-5 text-green-600" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Start'}
            </h3>
            {data.description && (
              <p className="text-xs text-gray-500 mt-1 truncate">
                {data.description}
              </p>
            )}
            
            {data.triggerType && (
              <Badge variant="secondary" className="mt-2 text-xs">
                {data.triggerType}
              </Badge>
            )}
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 border-2 border-green-400 bg-white"
        />
      </CardContent>
    </Card>
  );
};

export default StartNode;
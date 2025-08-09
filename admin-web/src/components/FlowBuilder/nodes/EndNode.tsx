import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Square, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

interface EndNodeData {
  label: string;
  description?: string;
  resultType?: 'success' | 'failure' | 'cancelled';
  returnValue?: any;
}

const resultIcons = {
  success: CheckCircle,
  failure: XCircle,
  cancelled: AlertTriangle,
};

const resultColors = {
  success: 'text-green-600 bg-green-100 border-green-200',
  failure: 'text-red-600 bg-red-100 border-red-200',
  cancelled: 'text-orange-600 bg-orange-100 border-orange-200',
};

const EndNode: React.FC<NodeProps<EndNodeData>> = ({ data, selected }) => {
  const ResultIcon = resultIcons[data.resultType || 'success'] || Square;
  const colorClass = resultColors[data.resultType || 'success'] || 'text-gray-600 bg-gray-100 border-gray-200';
  
  return (
    <Card className={`min-w-48 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : `border-red-200 hover:border-red-300`
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-red-400 bg-white"
        />
        
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
              <ResultIcon className="w-5 h-5" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'End'}
            </h3>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-1 truncate">
                {data.description}
              </p>
            )}
            
            {data.resultType && (
              <Badge 
                variant={data.resultType === 'success' ? 'default' : 'destructive'} 
                className="mt-2 text-xs"
              >
                {data.resultType}
              </Badge>
            )}
            
            {data.returnValue && (
              <div className="mt-2 text-xs font-mono bg-gray-100 rounded px-2 py-1 truncate">
                {JSON.stringify(data.returnValue)}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default EndNode;
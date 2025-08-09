import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { GitBranch, CheckCircle, XCircle } from 'lucide-react';

interface ConditionNodeData {
  label: string;
  condition: {
    field: string;
    operator: 'equals' | 'not_equals' | 'greater_than' | 'less_than' | 'contains' | 'exists';
    value: string | number;
  };
  description?: string;
}

const operatorLabels = {
  equals: '==',
  not_equals: '!=',
  greater_than: '>',
  less_than: '<',
  contains: 'contains',
  exists: 'exists',
};

const ConditionNode: React.FC<NodeProps<ConditionNodeData>> = ({ data, selected }) => {
  return (
    <Card className={`min-w-60 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-yellow-200 hover:border-yellow-300'
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-yellow-400 bg-white"
        />
        
        <div className="flex items-start space-x-3 mb-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 rounded-full bg-yellow-100 flex items-center justify-center">
              <GitBranch className="w-5 h-5 text-yellow-600" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Condition'}
            </h3>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-1">
                {data.description}
              </p>
            )}
          </div>
        </div>
        
        {/* Condition Details */}
        {data.condition && (
          <div className="bg-gray-50 rounded-lg p-3 mb-3 text-xs">
            <div className="font-mono text-center">
              <span className="text-blue-600">{data.condition.field}</span>
              <span className="mx-2 text-gray-500">
                {operatorLabels[data.condition.operator]}
              </span>
              <span className="text-purple-600">{data.condition.value}</span>
            </div>
          </div>
        )}
        
        {/* True/False Handles */}
        <div className="flex justify-between items-center">
          <div className="flex items-center space-x-1">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span className="text-xs font-medium text-green-600">True</span>
          </div>
          <div className="flex items-center space-x-1">
            <XCircle className="w-4 h-4 text-red-500" />
            <span className="text-xs font-medium text-red-600">False</span>
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Bottom}
          id="true"
          style={{ left: '25%', background: '#10b981' }}
          className="w-3 h-3 border-2 border-green-400"
        />
        
        <Handle
          type="source"
          position={Position.Bottom}
          id="false"
          style={{ left: '75%', background: '#ef4444' }}
          className="w-3 h-3 border-2 border-red-400"
        />
      </CardContent>
    </Card>
  );
};

export default ConditionNode;
import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Database, Variable, FileText, Code, Filter } from 'lucide-react';

interface DataNodeData {
  label: string;
  dataType: 'variable' | 'constant' | 'transform' | 'filter' | 'aggregate';
  description?: string;
  config: {
    variableName?: string;
    defaultValue?: any;
    dataSource?: string;
    transformRule?: string;
    filterCondition?: string;
  };
}

const dataIcons = {
  variable: Variable,
  constant: FileText,
  transform: Code,
  filter: Filter,
  aggregate: Database,
};

const dataColors = {
  variable: 'bg-purple-100 text-purple-600',
  constant: 'bg-gray-100 text-gray-600',
  transform: 'bg-blue-100 text-blue-600',
  filter: 'bg-yellow-100 text-yellow-600',
  aggregate: 'bg-indigo-100 text-indigo-600',
};

const DataNode: React.FC<NodeProps<DataNodeData>> = ({ data, selected }) => {
  const Icon = dataIcons[data.dataType] || Database;
  const colorClass = dataColors[data.dataType] || 'bg-gray-100 text-gray-600';
  
  return (
    <Card className={`min-w-56 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-purple-200 hover:border-purple-300'
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-purple-400 bg-white"
        />
        
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Data'}
            </h3>
            
            <Badge variant="outline" className="mt-1 text-xs">
              {data.dataType}
            </Badge>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-2">
                {data.description}
              </p>
            )}
            
            {/* Configuration Preview */}
            {data.config && (
              <div className="mt-3 space-y-2">
                {/* Variable Name */}
                {data.config.variableName && (
                  <div className="text-xs">
                    <span className="text-gray-500">Variable:</span>
                    <div className="mt-1 bg-purple-50 rounded px-2 py-1 font-mono text-purple-700">
                      ${data.config.variableName}
                    </div>
                  </div>
                )}
                
                {/* Default Value */}
                {data.config.defaultValue !== undefined && (
                  <div className="text-xs">
                    <span className="text-gray-500">Default:</span>
                    <div className="mt-1 bg-gray-50 rounded px-2 py-1 font-mono">
                      {typeof data.config.defaultValue === 'object' 
                        ? JSON.stringify(data.config.defaultValue)
                        : String(data.config.defaultValue)
                      }
                    </div>
                  </div>
                )}
                
                {/* Data Source */}
                {data.config.dataSource && (
                  <div className="text-xs">
                    <span className="text-gray-500">Source:</span>
                    <div className="mt-1 bg-blue-50 rounded px-2 py-1 text-blue-700">
                      {data.config.dataSource}
                    </div>
                  </div>
                )}
                
                {/* Transform Rule */}
                {data.config.transformRule && (
                  <div className="text-xs">
                    <span className="text-gray-500">Transform:</span>
                    <div className="mt-1 bg-yellow-50 rounded px-2 py-1 font-mono text-yellow-700 truncate">
                      {data.config.transformRule}
                    </div>
                  </div>
                )}
                
                {/* Filter Condition */}
                {data.config.filterCondition && (
                  <div className="text-xs">
                    <span className="text-gray-500">Filter:</span>
                    <div className="mt-1 bg-green-50 rounded px-2 py-1 font-mono text-green-700 truncate">
                      {data.config.filterCondition}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 border-2 border-purple-400 bg-white"
        />
      </CardContent>
    </Card>
  );
};

export default DataNode;
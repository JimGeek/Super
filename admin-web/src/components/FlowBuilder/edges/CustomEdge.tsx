import React from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  EdgeProps,
} from 'reactflow';
import { Badge } from '@/components/ui/badge';
import { X, CheckCircle, XCircle, ArrowRight } from 'lucide-react';

interface CustomEdgeData {
  label?: string;
  condition?: string;
  animated?: boolean;
  color?: string;
}

const CustomEdge: React.FC<EdgeProps<CustomEdgeData>> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeColor = data?.color || '#94a3b8';
  const strokeWidth = selected ? 3 : 2;
  const isAnimated = data?.animated ?? false;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: edgeColor,
          strokeWidth,
          strokeDasharray: isAnimated ? '5,5' : undefined,
        }}
        className={isAnimated ? 'animate-pulse' : ''}
      />
      
      {/* Edge Label */}
      {(data?.label || data?.condition) && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: 'all',
            }}
            className="nodrag nopan"
          >
            <div className="flex items-center space-x-2">
              {/* Condition-based icons */}
              {data?.condition === 'true' && (
                <CheckCircle className="w-4 h-4 text-green-500" />
              )}
              {data?.condition === 'false' && (
                <XCircle className="w-4 h-4 text-red-500" />
              )}
              {!data?.condition && data?.label && (
                <ArrowRight className="w-4 h-4 text-gray-500" />
              )}
              
              {/* Label Badge */}
              {data?.label && (
                <Badge 
                  variant="secondary" 
                  className="text-xs bg-white border shadow-sm"
                >
                  {data.label}
                </Badge>
              )}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

export default CustomEdge;
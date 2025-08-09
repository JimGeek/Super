import React, { useState, useCallback, useRef, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  ReactFlowProvider,
  ReactFlowInstance,
  NodeTypes,
  EdgeTypes,
} from 'reactflow';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { toast } from '@/components/ui/use-toast';
import {
  Play,
  Save,
  Download,
  Upload,
  Undo,
  Redo,
  ZoomIn,
  ZoomOut,
  Maximize,
  Grid,
  Settings,
  Eye,
  Code,
  FileText,
  Layers,
} from 'lucide-react';

import StartNode from './nodes/StartNode';
import EndNode from './nodes/EndNode';
import ActionNode from './nodes/ActionNode';
import ConditionNode from './nodes/ConditionNode';
import DataNode from './nodes/DataNode';
import TriggerNode from './nodes/TriggerNode';
import NotificationNode from './nodes/NotificationNode';
import PaymentNode from './nodes/PaymentNode';
import CustomEdge from './edges/CustomEdge';
import NodePalette from './NodePalette';
import FlowProperties from './FlowProperties';
import FlowSimulator from './FlowSimulator';

import 'reactflow/dist/style.css';

export interface FlowData {
  id: string;
  name: string;
  description: string;
  vertical: string;
  version: string;
  status: 'draft' | 'active' | 'inactive';
  nodes: Node[];
  edges: Edge[];
  metadata: {
    createdAt: string;
    updatedAt: string;
    createdBy: string;
    tags: string[];
  };
}

interface FlowBuilderProps {
  flow?: FlowData;
  onSave?: (flow: FlowData) => void;
  onPublish?: (flow: FlowData) => void;
  onTest?: (flow: FlowData) => void;
  readOnly?: boolean;
}

const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  action: ActionNode,
  condition: ConditionNode,
  data: DataNode,
  trigger: TriggerNode,
  notification: NotificationNode,
  payment: PaymentNode,
};

const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
};

const initialNodes: Node[] = [
  {
    id: 'start-1',
    type: 'start',
    position: { x: 100, y: 100 },
    data: { label: 'Start' },
  },
];

const FlowBuilder: React.FC<FlowBuilderProps> = ({
  flow,
  onSave,
  onPublish,
  onTest,
  readOnly = false,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    flow?.nodes || initialNodes
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(flow?.edges || []);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [activeTab, setActiveTab] = useState('design');
  const [isDirty, setIsDirty] = useState(false);
  const [isSimulating, setIsSimulating] = useState(false);
  const [flowProperties, setFlowProperties] = useState({
    name: flow?.name || 'New Flow',
    description: flow?.description || '',
    vertical: flow?.vertical || 'kirana',
    version: flow?.version || '1.0.0',
    status: flow?.status || 'draft' as const,
    tags: flow?.metadata?.tags || [],
  });

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // History management
  const [history, setHistory] = useState<{ nodes: Node[]; edges: Edge[] }[]>([
    { nodes: flow?.nodes || initialNodes, edges: flow?.edges || [] },
  ]);
  const [historyIndex, setHistoryIndex] = useState(0);

  const saveToHistory = useCallback(() => {
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({ nodes: [...nodes], edges: [...edges] });
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
    setIsDirty(true);
  }, [nodes, edges, history, historyIndex]);

  const undo = useCallback(() => {
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1];
      setNodes(prevState.nodes);
      setEdges(prevState.edges);
      setHistoryIndex(historyIndex - 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1];
      setNodes(nextState.nodes);
      setEdges(nextState.edges);
      setHistoryIndex(historyIndex + 1);
    }
  }, [history, historyIndex, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      const newEdge = {
        ...params,
        id: `edge-${Date.now()}`,
        type: 'custom',
        animated: true,
        data: { label: '' },
      };
      setEdges((eds) => addEdge(newEdge, eds));
      saveToHistory();
    },
    [setEdges, saveToHistory]
  );

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const addNode = useCallback(
    (nodeType: string, position?: { x: number; y: number }) => {
      const id = `${nodeType}-${Date.now()}`;
      const newNode: Node = {
        id,
        type: nodeType,
        position: position || { x: Math.random() * 400, y: Math.random() * 400 },
        data: getDefaultNodeData(nodeType),
      };
      setNodes((nds) => [...nds, newNode]);
      saveToHistory();
    },
    [setNodes, saveToHistory]
  );

  const updateNode = useCallback(
    (nodeId: string, newData: any) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId ? { ...node, data: { ...node.data, ...newData } } : node
        )
      );
      saveToHistory();
    },
    [setNodes, saveToHistory]
  );

  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
      setSelectedNode(null);
      saveToHistory();
    },
    [setNodes, setEdges, saveToHistory]
  );

  const handleSave = useCallback(() => {
    const flowData: FlowData = {
      id: flow?.id || `flow-${Date.now()}`,
      name: flowProperties.name,
      description: flowProperties.description,
      vertical: flowProperties.vertical,
      version: flowProperties.version,
      status: flowProperties.status,
      nodes,
      edges,
      metadata: {
        createdAt: flow?.metadata?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user', // TODO: Get from auth context
        tags: flowProperties.tags,
      },
    };

    onSave?.(flowData);
    setIsDirty(false);
    toast({
      title: 'Flow Saved',
      description: 'Your flow has been saved successfully.',
    });
  }, [flow, flowProperties, nodes, edges, onSave]);

  const handlePublish = useCallback(() => {
    const flowData: FlowData = {
      id: flow?.id || `flow-${Date.now()}`,
      name: flowProperties.name,
      description: flowProperties.description,
      vertical: flowProperties.vertical,
      version: flowProperties.version,
      status: 'active',
      nodes,
      edges,
      metadata: {
        createdAt: flow?.metadata?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user',
        tags: flowProperties.tags,
      },
    };

    onPublish?.(flowData);
    setFlowProperties(prev => ({ ...prev, status: 'active' }));
    setIsDirty(false);
    toast({
      title: 'Flow Published',
      description: 'Your flow is now active and can be used by merchants.',
    });
  }, [flow, flowProperties, nodes, edges, onPublish]);

  const handleTest = useCallback(() => {
    const flowData: FlowData = {
      id: flow?.id || `flow-${Date.now()}`,
      name: flowProperties.name,
      description: flowProperties.description,
      vertical: flowProperties.vertical,
      version: flowProperties.version,
      status: flowProperties.status,
      nodes,
      edges,
      metadata: {
        createdAt: flow?.metadata?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user',
        tags: flowProperties.tags,
      },
    };

    onTest?.(flowData);
    setIsSimulating(true);
    setActiveTab('simulate');
    toast({
      title: 'Flow Test Started',
      description: 'Testing your flow with sample data...',
    });
  }, [flow, flowProperties, nodes, edges, onTest]);

  const exportFlow = useCallback(() => {
    const flowData: FlowData = {
      id: flow?.id || `flow-${Date.now()}`,
      name: flowProperties.name,
      description: flowProperties.description,
      vertical: flowProperties.vertical,
      version: flowProperties.version,
      status: flowProperties.status,
      nodes,
      edges,
      metadata: {
        createdAt: flow?.metadata?.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        createdBy: 'current-user',
        tags: flowProperties.tags,
      },
    };

    const dataStr = JSON.stringify(flowData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${flowProperties.name.replace(/\s+/g, '_')}.json`;
    link.click();
    URL.revokeObjectURL(url);

    toast({
      title: 'Flow Exported',
      description: 'Flow has been exported as JSON file.',
    });
  }, [flow, flowProperties, nodes, edges]);

  const fitView = useCallback(() => {
    reactFlowInstance?.fitView({ padding: 0.2 });
  }, [reactFlowInstance]);

  const zoomIn = useCallback(() => {
    reactFlowInstance?.zoomIn();
  }, [reactFlowInstance]);

  const zoomOut = useCallback(() => {
    reactFlowInstance?.zoomOut();
  }, [reactFlowInstance]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (readOnly) return;

      if ((event.ctrlKey || event.metaKey)) {
        switch (event.key) {
          case 's':
            event.preventDefault();
            handleSave();
            break;
          case 'z':
            event.preventDefault();
            if (event.shiftKey) {
              redo();
            } else {
              undo();
            }
            break;
          case 'y':
            event.preventDefault();
            redo();
            break;
        }
      }

      if (event.key === 'Delete' && selectedNode) {
        deleteNode(selectedNode.id);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [readOnly, handleSave, undo, redo, selectedNode, deleteNode]);

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-card">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold">{flowProperties.name}</h1>
          <Badge variant={flowProperties.status === 'active' ? 'default' : 'secondary'}>
            {flowProperties.status}
          </Badge>
          {isDirty && <Badge variant="outline">Unsaved</Badge>}
        </div>

        <div className="flex items-center space-x-2">
          {!readOnly && (
            <>
              <Button variant="outline" size="sm" onClick={undo} disabled={historyIndex === 0}>
                <Undo className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={redo} disabled={historyIndex === history.length - 1}>
                <Redo className="w-4 h-4" />
              </Button>
              <Separator orientation="vertical" className="h-6" />
            </>
          )}

          <Button variant="outline" size="sm" onClick={zoomOut}>
            <ZoomOut className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={zoomIn}>
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={fitView}>
            <Maximize className="w-4 h-4" />
          </Button>

          <Separator orientation="vertical" className="h-6" />

          <Button variant="outline" size="sm" onClick={exportFlow}>
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>

          {!readOnly && (
            <>
              <Button variant="outline" size="sm" onClick={handleTest}>
                <Play className="w-4 h-4 mr-2" />
                Test
              </Button>
              <Button variant="outline" size="sm" onClick={handleSave}>
                <Save className="w-4 h-4 mr-2" />
                Save
              </Button>
              <Button onClick={handlePublish} size="sm">
                <Eye className="w-4 h-4 mr-2" />
                Publish
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          {/* Tab Navigation */}
          <div className="border-b bg-card px-4">
            <TabsList className="grid w-full max-w-md grid-cols-4">
              <TabsTrigger value="design" className="flex items-center space-x-2">
                <Grid className="w-4 h-4" />
                <span>Design</span>
              </TabsTrigger>
              <TabsTrigger value="properties" className="flex items-center space-x-2">
                <Settings className="w-4 h-4" />
                <span>Properties</span>
              </TabsTrigger>
              <TabsTrigger value="code" className="flex items-center space-x-2">
                <Code className="w-4 h-4" />
                <span>Code</span>
              </TabsTrigger>
              <TabsTrigger value="simulate" className="flex items-center space-x-2">
                <Play className="w-4 h-4" />
                <span>Simulate</span>
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab Content */}
          <div className="flex-1 flex">
            <TabsContent value="design" className="flex-1 flex m-0">
              {/* Node Palette */}
              {!readOnly && (
                <div className="w-80 border-r bg-card">
                  <NodePalette onAddNode={addNode} />
                </div>
              )}

              {/* Flow Canvas */}
              <div className="flex-1 relative" ref={reactFlowWrapper}>
                <ReactFlowProvider>
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onNodeClick={onNodeClick}
                    onPaneClick={onPaneClick}
                    onInit={setReactFlowInstance}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    defaultViewport={{ x: 0, y: 0, zoom: 1 }}
                    minZoom={0.1}
                    maxZoom={2}
                    snapToGrid
                    snapGrid={[10, 10]}
                    connectionLineType="smoothstep"
                    defaultEdgeOptions={{ type: 'custom', animated: true }}
                  >
                    <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
                    <Controls showInteractive={false} />
                    <MiniMap
                      nodeColor={(node) => getNodeColor(node.type || '')}
                      maskColor="rgba(255, 255, 255, 0.8)"
                      position="bottom-left"
                    />
                  </ReactFlow>
                </ReactFlowProvider>
              </div>

              {/* Properties Panel */}
              {selectedNode && (
                <div className="w-80 border-l bg-card">
                  <ScrollArea className="h-full">
                    <div className="p-4">
                      <h3 className="text-lg font-semibold mb-4">Node Properties</h3>
                      <NodePropertiesPanel
                        node={selectedNode}
                        onUpdateNode={updateNode}
                        onDeleteNode={deleteNode}
                      />
                    </div>
                  </ScrollArea>
                </div>
              )}
            </TabsContent>

            <TabsContent value="properties" className="flex-1 m-0">
              <FlowProperties
                properties={flowProperties}
                onChange={setFlowProperties}
                readOnly={readOnly}
              />
            </TabsContent>

            <TabsContent value="code" className="flex-1 m-0">
              <div className="p-4 h-full">
                <pre className="bg-muted p-4 rounded-md overflow-auto h-full text-sm">
                  {JSON.stringify({ nodes, edges }, null, 2)}
                </pre>
              </div>
            </TabsContent>

            <TabsContent value="simulate" className="flex-1 m-0">
              <FlowSimulator
                nodes={nodes}
                edges={edges}
                isRunning={isSimulating}
                onStop={() => setIsSimulating(false)}
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
};

// Helper functions
function getDefaultNodeData(nodeType: string) {
  switch (nodeType) {
    case 'start':
      return { label: 'Start', description: 'Flow starting point' };
    case 'end':
      return { label: 'End', description: 'Flow ending point' };
    case 'action':
      return { 
        label: 'Action', 
        actionType: 'http_request',
        config: {
          method: 'GET',
          url: '',
          headers: {},
          body: '',
        }
      };
    case 'condition':
      return { 
        label: 'Condition',
        condition: {
          field: '',
          operator: 'equals',
          value: '',
        }
      };
    case 'data':
      return { 
        label: 'Data',
        dataType: 'variable',
        config: {
          variableName: '',
          defaultValue: '',
        }
      };
    case 'trigger':
      return { 
        label: 'Trigger',
        triggerType: 'webhook',
        config: {
          url: '',
          method: 'POST',
        }
      };
    case 'notification':
      return { 
        label: 'Notification',
        notificationType: 'sms',
        config: {
          template: '',
          recipients: [],
        }
      };
    case 'payment':
      return { 
        label: 'Payment',
        paymentType: 'upi_collect',
        config: {
          amount: 0,
          description: '',
        }
      };
    default:
      return { label: 'Unknown' };
  }
}

function getNodeColor(nodeType: string): string {
  switch (nodeType) {
    case 'start': return '#10b981';
    case 'end': return '#ef4444';
    case 'action': return '#3b82f6';
    case 'condition': return '#f59e0b';
    case 'data': return '#8b5cf6';
    case 'trigger': return '#f97316';
    case 'notification': return '#06b6d4';
    case 'payment': return '#84cc16';
    default: return '#6b7280';
  }
}

// Node Properties Panel Component
interface NodePropertiesPanelProps {
  node: Node;
  onUpdateNode: (nodeId: string, newData: any) => void;
  onDeleteNode: (nodeId: string) => void;
}

const NodePropertiesPanel: React.FC<NodePropertiesPanelProps> = ({
  node,
  onUpdateNode,
  onDeleteNode,
}) => {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="text-sm font-medium mb-2">Basic Information</h4>
        <div className="space-y-2">
          <div>
            <label className="text-xs text-muted-foreground">Node ID</label>
            <div className="text-sm font-mono bg-muted p-2 rounded">{node.id}</div>
          </div>
          <div>
            <label className="text-xs text-muted-foreground">Type</label>
            <div className="text-sm bg-muted p-2 rounded">{node.type}</div>
          </div>
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-sm font-medium mb-2">Configuration</h4>
        {/* Node-specific configuration forms would go here */}
        <div className="text-sm text-muted-foreground">
          Node-specific properties panel coming soon...
        </div>
      </div>

      <Separator />

      <Button
        variant="destructive"
        size="sm"
        onClick={() => onDeleteNode(node.id)}
        className="w-full"
      >
        Delete Node
      </Button>
    </div>
  );
};

export default FlowBuilder;
import React, { useState, useEffect, useCallback } from 'react';
import { Node, Edge } from 'reactflow';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Play,
  Pause,
  Square,
  SkipForward,
  Rewind,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader,
  Database,
  Zap,
  Eye,
  Code,
  ArrowRight,
} from 'lucide-react';

interface FlowSimulatorProps {
  nodes: Node[];
  edges: Edge[];
  isRunning: boolean;
  onStop: () => void;
}

interface ExecutionStep {
  id: string;
  nodeId: string;
  nodeName: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  startTime?: number;
  endTime?: number;
  duration?: number;
  input?: any;
  output?: any;
  error?: string;
  logs: string[];
}

interface SimulationData {
  orderId: string;
  customerId: string;
  merchantId: string;
  amount: number;
  items: Array<{ name: string; quantity: number; price: number }>;
  customerPhone: string;
  merchantPhone: string;
  timestamp: string;
}

const FlowSimulator: React.FC<FlowSimulatorProps> = ({
  nodes,
  edges,
  isRunning,
  onStop,
}) => {
  const [executionSteps, setExecutionSteps] = useState<ExecutionStep[]>([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [simulationData, setSimulationData] = useState<SimulationData>({
    orderId: 'ORD-' + Math.random().toString(36).substr(2, 9).toUpperCase(),
    customerId: 'CUST-' + Math.random().toString(36).substr(2, 9).toUpperCase(),
    merchantId: 'MERCH-' + Math.random().toString(36).substr(2, 9).toUpperCase(),
    amount: 245.50,
    items: [
      { name: 'Rice Bag 1kg', quantity: 2, price: 45.00 },
      { name: 'Dal Toor 500g', quantity: 1, price: 85.00 },
      { name: 'Oil Sunflower 1L', quantity: 1, price: 115.50 },
    ],
    customerPhone: '+91 98765 43210',
    merchantPhone: '+91 87654 32109',
    timestamp: new Date().toISOString(),
  });
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [selectedStep, setSelectedStep] = useState<ExecutionStep | null>(null);

  // Initialize execution steps from flow nodes
  useEffect(() => {
    const steps: ExecutionStep[] = nodes.map((node, index) => ({
      id: `step-${index}`,
      nodeId: node.id,
      nodeName: node.data?.label || node.type || 'Unknown',
      status: 'pending',
      logs: [],
    }));
    
    setExecutionSteps(steps);
    setCurrentStepIndex(0);
  }, [nodes]);

  // Auto-play simulation
  useEffect(() => {
    if (!isPlaying || currentStepIndex >= executionSteps.length) {
      return;
    }

    const timer = setTimeout(() => {
      executeNextStep();
    }, 2000 / playbackSpeed);

    return () => clearTimeout(timer);
  }, [isPlaying, currentStepIndex, playbackSpeed, executionSteps.length]);

  const executeNextStep = useCallback(() => {
    if (currentStepIndex >= executionSteps.length) {
      setIsPlaying(false);
      return;
    }

    const currentStep = executionSteps[currentStepIndex];
    const node = nodes.find(n => n.id === currentStep.nodeId);

    setExecutionSteps(prev => prev.map((step, index) => {
      if (index === currentStepIndex) {
        return {
          ...step,
          status: 'running',
          startTime: Date.now(),
          logs: [...step.logs, `Executing ${step.nodeName}...`],
        };
      }
      return step;
    }));

    // Simulate execution based on node type
    setTimeout(() => {
      const success = Math.random() > 0.1; // 90% success rate
      const duration = Math.floor(Math.random() * 2000) + 500; // 0.5-2.5s

      setExecutionSteps(prev => prev.map((step, index) => {
        if (index === currentStepIndex) {
          const result = simulateNodeExecution(node, simulationData);
          return {
            ...step,
            status: success ? 'completed' : 'failed',
            endTime: Date.now(),
            duration,
            output: success ? result.output : undefined,
            error: success ? undefined : result.error,
            logs: [...step.logs, ...result.logs, success ? 'Completed successfully' : 'Execution failed'],
          };
        }
        return step;
      }));

      setCurrentStepIndex(prev => prev + 1);
    }, Math.floor(Math.random() * 1000) + 500);
  }, [currentStepIndex, executionSteps, nodes, simulationData]);

  const startSimulation = () => {
    setIsPlaying(true);
    if (currentStepIndex >= executionSteps.length) {
      // Reset simulation
      setCurrentStepIndex(0);
      setExecutionSteps(prev => prev.map(step => ({
        ...step,
        status: 'pending',
        startTime: undefined,
        endTime: undefined,
        duration: undefined,
        output: undefined,
        error: undefined,
        logs: [],
      })));
    }
  };

  const pauseSimulation = () => {
    setIsPlaying(false);
  };

  const stopSimulation = () => {
    setIsPlaying(false);
    setCurrentStepIndex(0);
    setExecutionSteps(prev => prev.map(step => ({
      ...step,
      status: 'pending',
      startTime: undefined,
      endTime: undefined,
      duration: undefined,
      output: undefined,
      error: undefined,
      logs: [],
    })));
    onStop();
  };

  const jumpToStep = (stepIndex: number) => {
    setCurrentStepIndex(stepIndex);
    setIsPlaying(false);
  };

  const progress = (currentStepIndex / executionSteps.length) * 100;
  const completedSteps = executionSteps.filter(step => step.status === 'completed').length;
  const failedSteps = executionSteps.filter(step => step.status === 'failed').length;

  return (
    <div className="h-full flex">
      {/* Simulation Controls & Data */}
      <div className="w-80 border-r bg-card">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            {/* Playback Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Play className="w-4 h-4" />
                  <span>Simulation Controls</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center space-x-2">
                  {!isPlaying ? (
                    <Button onClick={startSimulation} size="sm">
                      <Play className="w-4 h-4 mr-2" />
                      {currentStepIndex >= executionSteps.length ? 'Restart' : 'Play'}
                    </Button>
                  ) : (
                    <Button onClick={pauseSimulation} variant="outline" size="sm">
                      <Pause className="w-4 h-4 mr-2" />
                      Pause
                    </Button>
                  )}
                  <Button onClick={stopSimulation} variant="destructive" size="sm">
                    <Square className="w-4 h-4 mr-2" />
                    Stop
                  </Button>
                </div>

                <div>
                  <Label>Playback Speed</Label>
                  <div className="flex items-center space-x-2 mt-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPlaybackSpeed(0.5)}
                      className={playbackSpeed === 0.5 ? 'bg-primary text-primary-foreground' : ''}
                    >
                      0.5x
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPlaybackSpeed(1)}
                      className={playbackSpeed === 1 ? 'bg-primary text-primary-foreground' : ''}
                    >
                      1x
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPlaybackSpeed(2)}
                      className={playbackSpeed === 2 ? 'bg-primary text-primary-foreground' : ''}
                    >
                      2x
                    </Button>
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span>Progress</span>
                    <span>{Math.round(progress)}%</span>
                  </div>
                  <Progress value={progress} className="h-2" />
                </div>

                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-lg font-semibold text-green-600">{completedSteps}</div>
                    <div className="text-xs text-muted-foreground">Completed</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold text-red-600">{failedSteps}</div>
                    <div className="text-xs text-muted-foreground">Failed</div>
                  </div>
                  <div>
                    <div className="text-lg font-semibold">{executionSteps.length}</div>
                    <div className="text-xs text-muted-foreground">Total</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Test Data */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Database className="w-4 h-4" />
                  <span>Test Data</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <Label className="text-xs">Order ID</Label>
                  <Input
                    value={simulationData.orderId}
                    onChange={(e) => setSimulationData(prev => ({...prev, orderId: e.target.value}))}
                    className="h-8 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Customer Phone</Label>
                  <Input
                    value={simulationData.customerPhone}
                    onChange={(e) => setSimulationData(prev => ({...prev, customerPhone: e.target.value}))}
                    className="h-8 text-sm"
                  />
                </div>
                <div>
                  <Label className="text-xs">Amount</Label>
                  <Input
                    type="number"
                    value={simulationData.amount}
                    onChange={(e) => setSimulationData(prev => ({...prev, amount: parseFloat(e.target.value)}))}
                    className="h-8 text-sm"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </ScrollArea>
      </div>

      {/* Execution Timeline */}
      <div className="flex-1 flex flex-col">
        <div className="border-b p-4">
          <h3 className="text-lg font-semibold">Execution Timeline</h3>
        </div>
        
        <div className="flex-1 flex">
          {/* Steps List */}
          <div className="w-80 border-r">
            <ScrollArea className="h-full">
              <div className="p-4 space-y-2">
                {executionSteps.map((step, index) => (
                  <div
                    key={step.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      selectedStep?.id === step.id ? 'border-primary bg-primary/5' : ''
                    } ${
                      index === currentStepIndex ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => setSelectedStep(step)}
                  >
                    <div className="flex items-center space-x-3">
                      <div className="flex-shrink-0">
                        {step.status === 'pending' && (
                          <div className="w-6 h-6 rounded-full border-2 border-muted" />
                        )}
                        {step.status === 'running' && (
                          <Loader className="w-6 h-6 animate-spin text-blue-500" />
                        )}
                        {step.status === 'completed' && (
                          <CheckCircle className="w-6 h-6 text-green-500" />
                        )}
                        {step.status === 'failed' && (
                          <XCircle className="w-6 h-6 text-red-500" />
                        )}
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <h4 className="font-medium truncate">{step.nodeName}</h4>
                          <Badge variant="outline" className="text-xs">
                            {index + 1}
                          </Badge>
                        </div>
                        
                        {step.duration && (
                          <div className="text-xs text-muted-foreground flex items-center space-x-1 mt-1">
                            <Clock className="w-3 h-3" />
                            <span>{step.duration}ms</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>

          {/* Step Details */}
          <div className="flex-1">
            {selectedStep ? (
              <ScrollArea className="h-full">
                <div className="p-6 space-y-6">
                  <div className="flex items-center space-x-3">
                    <div>
                      {selectedStep.status === 'pending' && (
                        <div className="w-8 h-8 rounded-full border-2 border-muted" />
                      )}
                      {selectedStep.status === 'running' && (
                        <Loader className="w-8 h-8 animate-spin text-blue-500" />
                      )}
                      {selectedStep.status === 'completed' && (
                        <CheckCircle className="w-8 h-8 text-green-500" />
                      )}
                      {selectedStep.status === 'failed' && (
                        <XCircle className="w-8 h-8 text-red-500" />
                      )}
                    </div>
                    <div>
                      <h2 className="text-xl font-semibold">{selectedStep.nodeName}</h2>
                      <p className="text-muted-foreground">Node ID: {selectedStep.nodeId}</p>
                    </div>
                  </div>

                  {selectedStep.error && (
                    <Alert variant="destructive">
                      <AlertCircle className="h-4 w-4" />
                      <AlertDescription>{selectedStep.error}</AlertDescription>
                    </Alert>
                  )}

                  {/* Input/Output */}
                  <div className="grid grid-cols-2 gap-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center space-x-2">
                          <ArrowRight className="w-4 h-4 rotate-180" />
                          <span>Input</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-32">
                          {JSON.stringify(selectedStep.input || simulationData, null, 2)}
                        </pre>
                      </CardContent>
                    </Card>

                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm flex items-center space-x-2">
                          <ArrowRight className="w-4 h-4" />
                          <span>Output</span>
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="text-xs bg-muted p-3 rounded overflow-auto max-h-32">
                          {JSON.stringify(selectedStep.output || {}, null, 2)}
                        </pre>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Logs */}
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm flex items-center space-x-2">
                        <Eye className="w-4 h-4" />
                        <span>Execution Logs</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-1 max-h-48 overflow-auto">
                        {selectedStep.logs.map((log, index) => (
                          <div key={index} className="text-xs font-mono bg-muted p-2 rounded">
                            <span className="text-muted-foreground">
                              [{new Date().toISOString().split('T')[1].split('.')[0]}]
                            </span>
                            <span className="ml-2">{log}</span>
                          </div>
                        ))}
                        {selectedStep.logs.length === 0 && (
                          <div className="text-xs text-muted-foreground">No logs available</div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </ScrollArea>
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-muted-foreground">
                  <Code className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <h3 className="text-lg font-medium">Select a Step</h3>
                  <p className="text-sm">Click on a step to view its execution details</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to simulate node execution
function simulateNodeExecution(node: Node | undefined, data: SimulationData) {
  if (!node) {
    return {
      output: null,
      error: 'Node not found',
      logs: ['Error: Node not found'],
    };
  }

  const logs: string[] = [];
  
  switch (node.type) {
    case 'start':
      logs.push('Flow execution started');
      logs.push(`Processing order ${data.orderId}`);
      return {
        output: { flowId: 'flow-123', startTime: new Date().toISOString() },
        logs,
      };

    case 'notification':
      logs.push(`Sending notification to ${data.customerPhone}`);
      logs.push('SMS gateway connection established');
      logs.push('Message queued for delivery');
      return {
        output: { messageId: 'msg-' + Math.random().toString(36).substr(2, 9), sent: true },
        logs,
      };

    case 'payment':
      logs.push(`Processing payment of ₹${data.amount}`);
      logs.push('UPI collect request initiated');
      logs.push('Payment successful');
      return {
        output: { 
          transactionId: 'txn-' + Math.random().toString(36).substr(2, 9),
          amount: data.amount,
          status: 'completed'
        },
        logs,
      };

    case 'condition':
      const condition = Math.random() > 0.5;
      logs.push(`Evaluating condition: amount > 200`);
      logs.push(`Condition result: ${condition}`);
      return {
        output: { condition, branch: condition ? 'true' : 'false' },
        logs,
      };

    case 'action':
      logs.push('Executing HTTP request');
      logs.push('Request sent to external API');
      logs.push('Response received successfully');
      return {
        output: { 
          response: { status: 'success', data: { processed: true } },
          statusCode: 200
        },
        logs,
      };

    case 'end':
      logs.push('Flow execution completed');
      logs.push('Cleanup tasks performed');
      return {
        output: { completed: true, endTime: new Date().toISOString() },
        logs,
      };

    default:
      logs.push(`Executing ${node.type} node`);
      logs.push('Processing completed');
      return {
        output: { nodeType: node.type, processed: true },
        logs,
      };
  }
}

export default FlowSimulator;
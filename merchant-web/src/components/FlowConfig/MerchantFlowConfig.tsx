import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  Settings,
  Zap,
  Bell,
  MessageSquare,
  CreditCard,
  Clock,
  Users,
  Store,
  CheckCircle,
  XCircle,
  Eye,
  Edit,
  Save,
  Play,
  Pause,
  RotateCcw,
  Info,
  AlertTriangle,
  Smartphone,
  Mail,
  Calendar,
  Target,
  Workflow,
  Code,
  Database,
} from 'lucide-react';

interface FlowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  isActive: boolean;
  configuration: Record<string, any>;
  lastModified: string;
  usage: number;
}

interface FlowConfigSection {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  fields: FlowConfigField[];
}

interface FlowConfigField {
  id: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'switch' | 'number' | 'email' | 'phone';
  value: any;
  options?: { value: string; label: string }[];
  required?: boolean;
  description?: string;
}

const MerchantFlowConfig: React.FC = () => {
  const [selectedFlow, setSelectedFlow] = useState<string>('order_processing');
  const [isEditing, setIsEditing] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [isPreview, setIsPreview] = useState(false);

  // Mock flow templates
  const flowTemplates: FlowTemplate[] = [
    {
      id: 'order_processing',
      name: 'Order Processing',
      description: 'Automated workflow for handling new orders',
      category: 'Orders',
      isActive: true,
      configuration: {
        autoConfirm: true,
        confirmationDelay: 5,
        notifyCustomer: true,
        smsTemplate: 'Your order #{orderNumber} has been confirmed. ETA: {estimatedTime}',
        emailNotification: false,
        preparationTime: 15,
      },
      lastModified: '2024-12-01T10:30:00Z',
      usage: 245,
    },
    {
      id: 'payment_processing',
      name: 'Payment Processing',
      description: 'Handle payments and refunds automatically',
      category: 'Payments',
      isActive: true,
      configuration: {
        autoCapture: true,
        captureDelay: 0,
        refundPolicy: 'manual',
        notifyOnFailure: true,
        maxRetries: 3,
      },
      lastModified: '2024-11-28T15:45:00Z',
      usage: 198,
    },
    {
      id: 'inventory_management',
      name: 'Inventory Management',
      description: 'Automatic inventory updates and low stock alerts',
      category: 'Inventory',
      isActive: false,
      configuration: {
        autoDeduct: true,
        lowStockAlert: true,
        lowStockThreshold: 10,
        reorderPoint: 5,
        notifyOnOutOfStock: true,
      },
      lastModified: '2024-11-25T09:20:00Z',
      usage: 156,
    },
    {
      id: 'customer_notifications',
      name: 'Customer Notifications',
      description: 'Automated customer communication and updates',
      category: 'Communications',
      isActive: true,
      configuration: {
        orderConfirmation: true,
        statusUpdates: true,
        deliveryNotification: true,
        smsEnabled: true,
        emailEnabled: false,
        whatsappEnabled: true,
      },
      lastModified: '2024-12-01T08:15:00Z',
      usage: 312,
    },
  ];

  const [flows, setFlows] = useState(flowTemplates);

  // Configuration sections for the selected flow
  const getFlowConfigSections = (flowId: string): FlowConfigSection[] => {
    const flow = flows.find(f => f.id === flowId);
    if (!flow) return [];

    switch (flowId) {
      case 'order_processing':
        return [
          {
            id: 'basic',
            title: 'Basic Settings',
            description: 'Core order processing configuration',
            icon: <Settings className="h-5 w-5" />,
            fields: [
              {
                id: 'autoConfirm',
                label: 'Auto-confirm orders',
                type: 'switch',
                value: flow.configuration.autoConfirm,
                description: 'Automatically confirm orders when received',
              },
              {
                id: 'confirmationDelay',
                label: 'Confirmation delay (minutes)',
                type: 'number',
                value: flow.configuration.confirmationDelay,
                description: 'Delay before auto-confirming orders',
              },
              {
                id: 'preparationTime',
                label: 'Preparation time (minutes)',
                type: 'number',
                value: flow.configuration.preparationTime,
                description: 'Estimated time to prepare orders',
                required: true,
              },
            ],
          },
          {
            id: 'notifications',
            title: 'Customer Notifications',
            description: 'Configure customer communication',
            icon: <Bell className="h-5 w-5" />,
            fields: [
              {
                id: 'notifyCustomer',
                label: 'Send confirmation SMS',
                type: 'switch',
                value: flow.configuration.notifyCustomer,
                description: 'Send SMS when order is confirmed',
              },
              {
                id: 'smsTemplate',
                label: 'SMS template',
                type: 'textarea',
                value: flow.configuration.smsTemplate,
                description: 'Use {orderNumber}, {estimatedTime} as placeholders',
              },
              {
                id: 'emailNotification',
                label: 'Send email notifications',
                type: 'switch',
                value: flow.configuration.emailNotification,
                description: 'Send email confirmations to customers',
              },
            ],
          },
        ];

      case 'payment_processing':
        return [
          {
            id: 'capture',
            title: 'Payment Capture',
            description: 'Configure payment capture behavior',
            icon: <CreditCard className="h-5 w-5" />,
            fields: [
              {
                id: 'autoCapture',
                label: 'Auto-capture payments',
                type: 'switch',
                value: flow.configuration.autoCapture,
                description: 'Automatically capture authorized payments',
              },
              {
                id: 'captureDelay',
                label: 'Capture delay (minutes)',
                type: 'number',
                value: flow.configuration.captureDelay,
                description: 'Delay before capturing payments',
              },
              {
                id: 'maxRetries',
                label: 'Max retry attempts',
                type: 'number',
                value: flow.configuration.maxRetries,
                description: 'Maximum payment retry attempts',
              },
            ],
          },
          {
            id: 'refunds',
            title: 'Refund Policy',
            description: 'Configure refund handling',
            icon: <RotateCcw className="h-5 w-5" />,
            fields: [
              {
                id: 'refundPolicy',
                label: 'Refund processing',
                type: 'select',
                value: flow.configuration.refundPolicy,
                options: [
                  { value: 'manual', label: 'Manual approval required' },
                  { value: 'auto', label: 'Automatic processing' },
                  { value: 'conditional', label: 'Conditional based on amount' },
                ],
                description: 'How refunds should be processed',
              },
              {
                id: 'notifyOnFailure',
                label: 'Notify on payment failure',
                type: 'switch',
                value: flow.configuration.notifyOnFailure,
                description: 'Send alerts when payments fail',
              },
            ],
          },
        ];

      case 'customer_notifications':
        return [
          {
            id: 'channels',
            title: 'Communication Channels',
            description: 'Select notification channels',
            icon: <MessageSquare className="h-5 w-5" />,
            fields: [
              {
                id: 'smsEnabled',
                label: 'SMS notifications',
                type: 'switch',
                value: flow.configuration.smsEnabled,
                description: 'Send SMS notifications',
              },
              {
                id: 'emailEnabled',
                label: 'Email notifications',
                type: 'switch',
                value: flow.configuration.emailEnabled,
                description: 'Send email notifications',
              },
              {
                id: 'whatsappEnabled',
                label: 'WhatsApp notifications',
                type: 'switch',
                value: flow.configuration.whatsappEnabled,
                description: 'Send WhatsApp messages',
              },
            ],
          },
          {
            id: 'triggers',
            title: 'Notification Triggers',
            description: 'When to send notifications',
            icon: <Zap className="h-5 w-5" />,
            fields: [
              {
                id: 'orderConfirmation',
                label: 'Order confirmation',
                type: 'switch',
                value: flow.configuration.orderConfirmation,
                description: 'Notify when order is confirmed',
              },
              {
                id: 'statusUpdates',
                label: 'Status updates',
                type: 'switch',
                value: flow.configuration.statusUpdates,
                description: 'Notify on status changes',
              },
              {
                id: 'deliveryNotification',
                label: 'Delivery notification',
                type: 'switch',
                value: flow.configuration.deliveryNotification,
                description: 'Notify when order is delivered',
              },
            ],
          },
        ];

      default:
        return [];
    }
  };

  const currentFlow = flows.find(f => f.id === selectedFlow);
  const configSections = getFlowConfigSections(selectedFlow);

  const updateFieldValue = (sectionId: string, fieldId: string, value: any) => {
    setFlows(prevFlows =>
      prevFlows.map(flow =>
        flow.id === selectedFlow
          ? {
              ...flow,
              configuration: {
                ...flow.configuration,
                [fieldId]: value,
              },
            }
          : flow
      )
    );
    setHasChanges(true);
  };

  const toggleFlowActive = (flowId: string) => {
    setFlows(prevFlows =>
      prevFlows.map(flow =>
        flow.id === flowId
          ? { ...flow, isActive: !flow.isActive }
          : flow
      )
    );
    setHasChanges(true);
  };

  const saveChanges = () => {
    // In real app, this would save to backend
    console.log('Saving flow configuration...', currentFlow);
    setHasChanges(false);
    setIsEditing(false);
  };

  const testFlow = () => {
    console.log('Testing flow...', selectedFlow);
    // Implement flow testing logic
  };

  const renderField = (section: FlowConfigSection, field: FlowConfigField) => {
    const fieldId = `${section.id}-${field.id}`;
    
    switch (field.type) {
      case 'switch':
        return (
          <div key={fieldId} className="flex items-center justify-between space-x-2">
            <div className="space-y-1">
              <Label htmlFor={fieldId}>{field.label}</Label>
              {field.description && (
                <p className="text-sm text-muted-foreground">{field.description}</p>
              )}
            </div>
            <Switch
              id={fieldId}
              checked={field.value}
              onCheckedChange={(checked) => updateFieldValue(section.id, field.id, checked)}
              disabled={!isEditing}
            />
          </div>
        );

      case 'number':
        return (
          <div key={fieldId} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type="number"
              value={field.value}
              onChange={(e) => updateFieldValue(section.id, field.id, parseInt(e.target.value))}
              disabled={!isEditing}
            />
            {field.description && (
              <p className="text-sm text-muted-foreground">{field.description}</p>
            )}
          </div>
        );

      case 'textarea':
        return (
          <div key={fieldId} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Textarea
              id={fieldId}
              value={field.value}
              onChange={(e) => updateFieldValue(section.id, field.id, e.target.value)}
              disabled={!isEditing}
              rows={3}
            />
            {field.description && (
              <p className="text-sm text-muted-foreground">{field.description}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={fieldId} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Select
              value={field.value}
              onValueChange={(value) => updateFieldValue(section.id, field.id, value)}
              disabled={!isEditing}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {field.options?.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {field.description && (
              <p className="text-sm text-muted-foreground">{field.description}</p>
            )}
          </div>
        );

      default:
        return (
          <div key={fieldId} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              type={field.type}
              value={field.value}
              onChange={(e) => updateFieldValue(section.id, field.id, e.target.value)}
              disabled={!isEditing}
            />
            {field.description && (
              <p className="text-sm text-muted-foreground">{field.description}</p>
            )}
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Flow Configuration</h1>
          <p className="text-muted-foreground">
            Customize your business workflows to automate operations
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {hasChanges && (
            <Alert className="w-auto">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>You have unsaved changes</AlertDescription>
            </Alert>
          )}
          
          <Button variant="outline" onClick={testFlow}>
            <Play className="h-4 w-4 mr-2" />
            Test Flow
          </Button>
          
          {isEditing ? (
            <>
              <Button variant="outline" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
              <Button onClick={saveChanges} disabled={!hasChanges}>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </>
          ) : (
            <Button onClick={() => setIsEditing(true)}>
              <Edit className="h-4 w-4 mr-2" />
              Edit Flows
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Flow List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Workflow className="h-5 w-5" />
                <span>Available Flows</span>
              </CardTitle>
              <CardDescription>Select a flow to configure</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-96">
                <div className="space-y-2">
                  {flows.map((flow) => (
                    <Card
                      key={flow.id}
                      className={`cursor-pointer transition-colors ${
                        selectedFlow === flow.id
                          ? 'border-primary bg-primary/5'
                          : 'hover:bg-muted/50'
                      }`}
                      onClick={() => setSelectedFlow(flow.id)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{flow.name}</h4>
                          <Switch
                            checked={flow.isActive}
                            onCheckedChange={() => toggleFlowActive(flow.id)}
                            onClick={(e) => e.stopPropagation()}
                            disabled={!isEditing}
                          />
                        </div>
                        
                        <p className="text-sm text-muted-foreground mb-3">
                          {flow.description}
                        </p>
                        
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <Badge variant="outline">{flow.category}</Badge>
                          <span>{flow.usage} uses</span>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Flow Configuration */}
        <div className="lg:col-span-3">
          {currentFlow ? (
            <div className="space-y-6">
              {/* Flow Overview */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="flex items-center space-x-2">
                        <Settings className="h-5 w-5" />
                        <span>{currentFlow.name}</span>
                        <Badge variant={currentFlow.isActive ? 'default' : 'secondary'}>
                          {currentFlow.isActive ? 'Active' : 'Inactive'}
                        </Badge>
                      </CardTitle>
                      <CardDescription>{currentFlow.description}</CardDescription>
                    </div>
                    
                    <div className="text-sm text-muted-foreground">
                      <div>Used {currentFlow.usage} times</div>
                      <div>Last modified: {new Date(currentFlow.lastModified).toLocaleDateString()}</div>
                    </div>
                  </div>
                </CardHeader>
              </Card>

              {/* Configuration Sections */}
              <div className="space-y-6">
                {configSections.map((section) => (
                  <Card key={section.id}>
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        {section.icon}
                        <span>{section.title}</span>
                      </CardTitle>
                      <CardDescription>{section.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {section.fields.map((field) => renderField(section, field))}
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Flow Actions */}
              {isEditing && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center space-x-2">
                      <Target className="h-5 w-5" />
                      <span>Flow Actions</span>
                    </CardTitle>
                    <CardDescription>Advanced flow management options</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-4">
                      <Button variant="outline">
                        <Code className="h-4 w-4 mr-2" />
                        View JSON
                      </Button>
                      
                      <Button variant="outline">
                        <Database className="h-4 w-4 mr-2" />
                        Export Template
                      </Button>
                      
                      <Button variant="outline">
                        <Eye className="h-4 w-4 mr-2" />
                        Preview Flow
                      </Button>
                      
                      <Button variant="outline">
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Reset to Default
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="pt-6">
                <div className="text-center py-12">
                  <Workflow className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">Select a Flow</h3>
                  <p className="text-muted-foreground">
                    Choose a flow from the left panel to start configuring
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default MerchantFlowConfig;
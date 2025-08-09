import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Settings,
  Tag,
  Info,
  Shield,
  Zap,
  Clock,
  Users,
  FileText,
  Plus,
  X,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react';

interface FlowPropertiesData {
  name: string;
  description: string;
  vertical: string;
  version: string;
  status: 'draft' | 'active' | 'inactive';
  tags: string[];
}

interface FlowPropertiesProps {
  properties: FlowPropertiesData;
  onChange: (properties: FlowPropertiesData) => void;
  readOnly?: boolean;
}

const verticals = [
  { id: 'kirana', name: 'Kirana Store', description: 'Grocery and convenience stores' },
  { id: 'barber', name: 'Barber Shop', description: 'Hair cutting and grooming services' },
  { id: 'garage', name: 'Auto Garage', description: 'Vehicle repair and maintenance' },
  { id: 'water_purifier', name: 'Water Purifier', description: 'Water purification services' },
  { id: 'pharmacy', name: 'Pharmacy', description: 'Medicine and healthcare products' },
  { id: 'restaurant', name: 'Restaurant', description: 'Food and beverage services' },
  { id: 'electronics', name: 'Electronics', description: 'Electronic goods and repairs' },
  { id: 'clothing', name: 'Clothing', description: 'Apparel and fashion' },
  { id: 'home_services', name: 'Home Services', description: 'Cleaning, repairs, and maintenance' },
  { id: 'beauty', name: 'Beauty Salon', description: 'Beauty and wellness services' },
];

const statusOptions = [
  { value: 'draft', label: 'Draft', description: 'Work in progress, not available to merchants', icon: FileText },
  { value: 'active', label: 'Active', description: 'Live and available to merchants', icon: CheckCircle },
  { value: 'inactive', label: 'Inactive', description: 'Temporarily disabled', icon: AlertTriangle },
];

const FlowProperties: React.FC<FlowPropertiesProps> = ({
  properties,
  onChange,
  readOnly = false,
}) => {
  const [newTag, setNewTag] = useState('');

  const updateProperty = (key: keyof FlowPropertiesData, value: any) => {
    if (readOnly) return;
    onChange({ ...properties, [key]: value });
  };

  const addTag = () => {
    if (newTag.trim() && !properties.tags.includes(newTag.trim())) {
      updateProperty('tags', [...properties.tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    updateProperty('tags', properties.tags.filter(tag => tag !== tagToRemove));
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      addTag();
    }
  };

  const selectedVertical = verticals.find(v => v.id === properties.vertical);
  const selectedStatus = statusOptions.find(s => s.value === properties.status);

  return (
    <div className="h-full">
      <ScrollArea className="h-full">
        <div className="p-6 space-y-6">
          <div className="flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Flow Properties</h2>
          </div>

          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general" className="flex items-center space-x-2">
                <Info className="w-4 h-4" />
                <span className="hidden sm:inline">General</span>
              </TabsTrigger>
              <TabsTrigger value="settings" className="flex items-center space-x-2">
                <Zap className="w-4 h-4" />
                <span className="hidden sm:inline">Settings</span>
              </TabsTrigger>
              <TabsTrigger value="permissions" className="flex items-center space-x-2">
                <Shield className="w-4 h-4" />
                <span className="hidden sm:inline">Access</span>
              </TabsTrigger>
              <TabsTrigger value="metadata" className="flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span className="hidden sm:inline">Metadata</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-6 mt-6">
              {/* Basic Information */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Info className="w-4 h-4" />
                    <span>Basic Information</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Flow Name</Label>
                      <Input
                        id="name"
                        placeholder="Enter flow name"
                        value={properties.name}
                        onChange={(e) => updateProperty('name', e.target.value)}
                        disabled={readOnly}
                      />
                    </div>
                    <div>
                      <Label htmlFor="version">Version</Label>
                      <Input
                        id="version"
                        placeholder="1.0.0"
                        value={properties.version}
                        onChange={(e) => updateProperty('version', e.target.value)}
                        disabled={readOnly}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Describe what this flow does..."
                      value={properties.description}
                      onChange={(e) => updateProperty('description', e.target.value)}
                      disabled={readOnly}
                      rows={3}
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="vertical">Business Vertical</Label>
                      <Select
                        value={properties.vertical}
                        onValueChange={(value) => updateProperty('vertical', value)}
                        disabled={readOnly}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select vertical" />
                        </SelectTrigger>
                        <SelectContent>
                          {verticals.map(vertical => (
                            <SelectItem key={vertical.id} value={vertical.id}>
                              <div>
                                <div className="font-medium">{vertical.name}</div>
                                <div className="text-xs text-muted-foreground">
                                  {vertical.description}
                                </div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {selectedVertical && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {selectedVertical.description}
                        </p>
                      )}
                    </div>

                    <div>
                      <Label htmlFor="status">Status</Label>
                      <Select
                        value={properties.status}
                        onValueChange={(value: 'draft' | 'active' | 'inactive') => 
                          updateProperty('status', value)
                        }
                        disabled={readOnly}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          {statusOptions.map(status => {
                            const Icon = status.icon;
                            return (
                              <SelectItem key={status.value} value={status.value}>
                                <div className="flex items-center space-x-2">
                                  <Icon className="w-4 h-4" />
                                  <div>
                                    <div className="font-medium">{status.label}</div>
                                    <div className="text-xs text-muted-foreground">
                                      {status.description}
                                    </div>
                                  </div>
                                </div>
                              </SelectItem>
                            );
                          })}
                        </SelectContent>
                      </Select>
                      {selectedStatus && (
                        <p className="text-sm text-muted-foreground mt-1">
                          {selectedStatus.description}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Tags */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Tag className="w-4 h-4" />
                    <span>Tags</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex flex-wrap gap-2">
                    {properties.tags.map(tag => (
                      <Badge key={tag} variant="secondary" className="flex items-center space-x-1">
                        <span>{tag}</span>
                        {!readOnly && (
                          <button
                            onClick={() => removeTag(tag)}
                            className="ml-1 hover:bg-destructive hover:text-destructive-foreground rounded-full p-0.5"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        )}
                      </Badge>
                    ))}
                  </div>

                  {!readOnly && (
                    <div className="flex space-x-2">
                      <Input
                        placeholder="Add a tag..."
                        value={newTag}
                        onChange={(e) => setNewTag(e.target.value)}
                        onKeyPress={handleKeyPress}
                      />
                      <Button onClick={addTag} size="sm">
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="settings" className="space-y-6 mt-6">
              {/* Execution Settings */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Zap className="w-4 h-4" />
                    <span>Execution Settings</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="auto-retry">Auto Retry on Failure</Label>
                      <p className="text-sm text-muted-foreground">
                        Automatically retry failed steps
                      </p>
                    </div>
                    <Switch id="auto-retry" disabled={readOnly} />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="parallel-execution">Parallel Execution</Label>
                      <p className="text-sm text-muted-foreground">
                        Allow parallel execution of independent branches
                      </p>
                    </div>
                    <Switch id="parallel-execution" disabled={readOnly} />
                  </div>

                  <Separator />

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="timeout">Timeout (seconds)</Label>
                      <Input
                        id="timeout"
                        type="number"
                        placeholder="300"
                        disabled={readOnly}
                      />
                    </div>
                    <div>
                      <Label htmlFor="retry-count">Max Retry Attempts</Label>
                      <Input
                        id="retry-count"
                        type="number"
                        placeholder="3"
                        disabled={readOnly}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Rate Limiting */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Clock className="w-4 h-4" />
                    <span>Rate Limiting</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="rate-limit">Executions per minute</Label>
                      <Input
                        id="rate-limit"
                        type="number"
                        placeholder="100"
                        disabled={readOnly}
                      />
                    </div>
                    <div>
                      <Label htmlFor="burst-limit">Burst limit</Label>
                      <Input
                        id="burst-limit"
                        type="number"
                        placeholder="10"
                        disabled={readOnly}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="cooldown">Cooldown period (seconds)</Label>
                    <Input
                      id="cooldown"
                      type="number"
                      placeholder="60"
                      disabled={readOnly}
                    />
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="permissions" className="space-y-6 mt-6">
              {/* Access Control */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Shield className="w-4 h-4" />
                    <span>Access Control</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="public-access">Public Access</Label>
                      <p className="text-sm text-muted-foreground">
                        Allow all merchants to use this flow
                      </p>
                    </div>
                    <Switch id="public-access" disabled={readOnly} defaultChecked />
                  </div>

                  <Separator />

                  <div className="flex items-center justify-between">
                    <div>
                      <Label htmlFor="require-approval">Require Approval</Label>
                      <p className="text-sm text-muted-foreground">
                        Merchants must request access to use this flow
                      </p>
                    </div>
                    <Switch id="require-approval" disabled={readOnly} />
                  </div>

                  <Separator />

                  <div>
                    <Label htmlFor="allowed-roles">Allowed Roles</Label>
                    <Select disabled={readOnly}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select roles..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">Administrator</SelectItem>
                        <SelectItem value="merchant">Merchant</SelectItem>
                        <SelectItem value="operator">Operator</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>

              {/* Merchant Groups */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Users className="w-4 h-4" />
                    <span>Merchant Groups</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="merchant-groups">Allowed Merchant Groups</Label>
                    <Select disabled={readOnly}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select groups..." />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="premium">Premium Merchants</SelectItem>
                        <SelectItem value="verified">Verified Merchants</SelectItem>
                        <SelectItem value="beta">Beta Testers</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <Badge variant="outline">Premium Merchants</Badge>
                    <Badge variant="outline">Verified Merchants</Badge>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="metadata" className="space-y-6 mt-6">
              {/* Documentation */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <FileText className="w-4 h-4" />
                    <span>Documentation</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="usage-notes">Usage Notes</Label>
                    <Textarea
                      id="usage-notes"
                      placeholder="Add notes about how to use this flow..."
                      disabled={readOnly}
                      rows={4}
                    />
                  </div>

                  <div>
                    <Label htmlFor="changelog">Changelog</Label>
                    <Textarea
                      id="changelog"
                      placeholder="Document changes in this version..."
                      disabled={readOnly}
                      rows={4}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Analytics */}
              <Card>
                <CardHeader>
                  <CardTitle>Flow Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-2xl font-bold">1,247</div>
                      <div className="text-sm text-muted-foreground">Total Executions</div>
                    </div>
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-2xl font-bold">98.2%</div>
                      <div className="text-sm text-muted-foreground">Success Rate</div>
                    </div>
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-2xl font-bold">2.3s</div>
                      <div className="text-sm text-muted-foreground">Avg Duration</div>
                    </div>
                    <div className="text-center p-4 bg-muted rounded-lg">
                      <div className="text-2xl font-bold">156</div>
                      <div className="text-sm text-muted-foreground">Active Users</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </ScrollArea>
    </div>
  );
};

export default FlowProperties;
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Search,
  Play,
  Square,
  Zap,
  Database,
  GitBranch,
  Bell,
  CreditCard,
  Webhook,
  Mail,
  MessageSquare,
  Calculator,
  Timer,
  Filter,
  Shuffle,
  Archive,
  Settings,
  Code,
  Globe,
  Smartphone,
} from 'lucide-react';

interface NodeType {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  category: string;
  color: string;
  tags: string[];
}

interface NodePaletteProps {
  onAddNode: (nodeType: string, position?: { x: number; y: number }) => void;
}

const nodeTypes: NodeType[] = [
  // Flow Control
  {
    id: 'start',
    name: 'Start',
    description: 'Entry point for the flow',
    icon: <Play className="w-4 h-4" />,
    category: 'Flow Control',
    color: 'bg-green-100 text-green-700',
    tags: ['entry', 'begin'],
  },
  {
    id: 'end',
    name: 'End',
    description: 'Exit point for the flow',
    icon: <Square className="w-4 h-4" />,
    category: 'Flow Control',
    color: 'bg-red-100 text-red-700',
    tags: ['exit', 'finish'],
  },
  {
    id: 'condition',
    name: 'Condition',
    description: 'Branch flow based on conditions',
    icon: <GitBranch className="w-4 h-4" />,
    category: 'Flow Control',
    color: 'bg-yellow-100 text-yellow-700',
    tags: ['if', 'branch', 'decision'],
  },

  // Actions
  {
    id: 'action',
    name: 'Action',
    description: 'Perform HTTP requests and API calls',
    icon: <Zap className="w-4 h-4" />,
    category: 'Actions',
    color: 'bg-blue-100 text-blue-700',
    tags: ['http', 'api', 'request'],
  },
  {
    id: 'data',
    name: 'Data',
    description: 'Store and manipulate data',
    icon: <Database className="w-4 h-4" />,
    category: 'Actions',
    color: 'bg-purple-100 text-purple-700',
    tags: ['variable', 'storage', 'transform'],
  },
  {
    id: 'calculator',
    name: 'Calculator',
    description: 'Perform mathematical operations',
    icon: <Calculator className="w-4 h-4" />,
    category: 'Actions',
    color: 'bg-indigo-100 text-indigo-700',
    tags: ['math', 'calculate', 'formula'],
  },
  {
    id: 'timer',
    name: 'Timer',
    description: 'Add delays or schedule actions',
    icon: <Timer className="w-4 h-4" />,
    category: 'Actions',
    color: 'bg-gray-100 text-gray-700',
    tags: ['delay', 'schedule', 'wait'],
  },

  // Triggers
  {
    id: 'trigger',
    name: 'Webhook',
    description: 'Trigger flow via webhook',
    icon: <Webhook className="w-4 h-4" />,
    category: 'Triggers',
    color: 'bg-orange-100 text-orange-700',
    tags: ['webhook', 'external', 'trigger'],
  },
  {
    id: 'schedule',
    name: 'Schedule',
    description: 'Trigger flow on schedule',
    icon: <Timer className="w-4 h-4" />,
    category: 'Triggers',
    color: 'bg-emerald-100 text-emerald-700',
    tags: ['cron', 'schedule', 'periodic'],
  },
  {
    id: 'event',
    name: 'Event',
    description: 'Trigger on system events',
    icon: <Bell className="w-4 h-4" />,
    category: 'Triggers',
    color: 'bg-pink-100 text-pink-700',
    tags: ['event', 'system', 'listener'],
  },

  // Communications
  {
    id: 'notification',
    name: 'Notification',
    description: 'Send push notifications',
    icon: <Bell className="w-4 h-4" />,
    category: 'Communications',
    color: 'bg-cyan-100 text-cyan-700',
    tags: ['push', 'notify', 'alert'],
  },
  {
    id: 'sms',
    name: 'SMS',
    description: 'Send SMS messages',
    icon: <MessageSquare className="w-4 h-4" />,
    category: 'Communications',
    color: 'bg-green-100 text-green-700',
    tags: ['sms', 'text', 'message'],
  },
  {
    id: 'email',
    name: 'Email',
    description: 'Send email messages',
    icon: <Mail className="w-4 h-4" />,
    category: 'Communications',
    color: 'bg-blue-100 text-blue-700',
    tags: ['email', 'mail', 'message'],
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    description: 'Send WhatsApp messages',
    icon: <Smartphone className="w-4 h-4" />,
    category: 'Communications',
    color: 'bg-green-100 text-green-700',
    tags: ['whatsapp', 'wa', 'message'],
  },

  // Payments
  {
    id: 'payment',
    name: 'Payment',
    description: 'Process UPI payments',
    icon: <CreditCard className="w-4 h-4" />,
    category: 'Payments',
    color: 'bg-lime-100 text-lime-700',
    tags: ['upi', 'payment', 'transaction'],
  },
  {
    id: 'refund',
    name: 'Refund',
    description: 'Process payment refunds',
    icon: <Archive className="w-4 h-4" />,
    category: 'Payments',
    color: 'bg-orange-100 text-orange-700',
    tags: ['refund', 'reverse', 'payment'],
  },

  // Utilities
  {
    id: 'filter',
    name: 'Filter',
    description: 'Filter and transform data',
    icon: <Filter className="w-4 h-4" />,
    category: 'Utilities',
    color: 'bg-teal-100 text-teal-700',
    tags: ['filter', 'transform', 'data'],
  },
  {
    id: 'random',
    name: 'Random',
    description: 'Generate random values',
    icon: <Shuffle className="w-4 h-4" />,
    category: 'Utilities',
    color: 'bg-violet-100 text-violet-700',
    tags: ['random', 'generate', 'value'],
  },
  {
    id: 'code',
    name: 'Code',
    description: 'Execute custom JavaScript code',
    icon: <Code className="w-4 h-4" />,
    category: 'Utilities',
    color: 'bg-slate-100 text-slate-700',
    tags: ['javascript', 'code', 'custom'],
  },
  {
    id: 'http',
    name: 'HTTP',
    description: 'Make HTTP requests to external APIs',
    icon: <Globe className="w-4 h-4" />,
    category: 'Utilities',
    color: 'bg-sky-100 text-sky-700',
    tags: ['http', 'api', 'external'],
  },
];

const NodePalette: React.FC<NodePaletteProps> = ({ onAddNode }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = Array.from(new Set(nodeTypes.map(node => node.category)));

  const filteredNodes = nodeTypes.filter(node => {
    const matchesSearch = searchTerm === '' || 
      node.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      node.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      node.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesCategory = selectedCategory === null || node.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  const handleDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center space-x-2">
          <Settings className="w-5 h-5" />
          <span>Node Palette</span>
        </CardTitle>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <Input
            placeholder="Search nodes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap gap-1">
          <Button
            variant={selectedCategory === null ? "default" : "outline"}
            size="sm"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Button>
          {categories.map(category => (
            <Button
              key={category}
              variant={selectedCategory === category ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(category)}
            >
              {category}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <ScrollArea className="h-[calc(100vh-300px)]">
          <div className="p-4 space-y-4">
            {categories
              .filter(category => 
                selectedCategory === null || selectedCategory === category
              )
              .map(category => {
                const categoryNodes = filteredNodes.filter(node => node.category === category);
                
                if (categoryNodes.length === 0) return null;

                return (
                  <div key={category}>
                    {selectedCategory === null && (
                      <>
                        <h3 className="text-sm font-semibold text-muted-foreground mb-2">
                          {category}
                        </h3>
                        <Separator className="mb-3" />
                      </>
                    )}
                    
                    <div className="grid gap-2">
                      {categoryNodes.map(node => (
                        <div
                          key={node.id}
                          className="p-3 border rounded-lg cursor-move hover:bg-accent transition-colors"
                          draggable
                          onDragStart={(e) => handleDragStart(e, node.id)}
                          onClick={() => onAddNode(node.id)}
                        >
                          <div className="flex items-start space-x-3">
                            <div className={`p-2 rounded-md ${node.color}`}>
                              {node.icon}
                            </div>
                            
                            <div className="flex-1 min-w-0">
                              <h4 className="text-sm font-medium">{node.name}</h4>
                              <p className="text-xs text-muted-foreground mt-1">
                                {node.description}
                              </p>
                              
                              <div className="flex flex-wrap gap-1 mt-2">
                                {node.tags.slice(0, 3).map(tag => (
                                  <Badge key={tag} variant="secondary" className="text-xs">
                                    {tag}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}

            {filteredNodes.length === 0 && (
              <div className="text-center text-muted-foreground py-8">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No nodes found</p>
                <p className="text-xs">Try adjusting your search or category filter</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default NodePalette;
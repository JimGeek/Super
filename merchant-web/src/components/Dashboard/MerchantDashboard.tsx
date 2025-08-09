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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  ShoppingBag,
  IndianRupee,
  Clock,
  Users,
  TrendingUp,
  TrendingDown,
  Eye,
  Phone,
  MapPin,
  Calendar,
  CheckCircle,
  XCircle,
  AlertCircle,
  Package,
  Truck,
  Star,
  Bell,
  Settings,
  MoreHorizontal,
  Search,
  Filter,
  Download,
  RefreshCw,
  Plus,
  Edit,
  Trash2,
} from 'lucide-react';

interface Order {
  id: string;
  orderNumber: string;
  customer: {
    name: string;
    phone: string;
    address: string;
  };
  items: Array<{
    name: string;
    quantity: number;
    price: number;
  }>;
  totalAmount: number;
  status: 'placed' | 'confirmed' | 'preparing' | 'ready' | 'picked_up' | 'delivered' | 'cancelled';
  createdAt: string;
  estimatedDelivery?: string;
  paymentStatus: 'pending' | 'paid' | 'failed';
  priority: 'normal' | 'high' | 'urgent';
}

interface DashboardMetrics {
  todayOrders: number;
  todayRevenue: number;
  pendingOrders: number;
  completedOrders: number;
  averageOrderValue: number;
  customerSatisfaction: number;
}

const MerchantDashboard: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('today');
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  // Mock data - in real app, this would come from API
  const metrics: DashboardMetrics = {
    todayOrders: 47,
    todayRevenue: 12450,
    pendingOrders: 8,
    completedOrders: 39,
    averageOrderValue: 264.89,
    customerSatisfaction: 4.8,
  };

  const salesData = [
    { date: '6 AM', orders: 2, revenue: 450 },
    { date: '9 AM', orders: 8, revenue: 1200 },
    { date: '12 PM', orders: 15, revenue: 2800 },
    { date: '3 PM', orders: 12, revenue: 2200 },
    { date: '6 PM', orders: 18, revenue: 3400 },
    { date: '9 PM', orders: 22, revenue: 4200 },
    { date: '12 AM', orders: 8, revenue: 800 },
  ];

  const weeklyData = [
    { day: 'Mon', orders: 45, revenue: 11200 },
    { day: 'Tue', orders: 52, revenue: 13800 },
    { day: 'Wed', orders: 38, revenue: 9600 },
    { day: 'Thu', orders: 61, revenue: 15400 },
    { day: 'Fri', orders: 48, revenue: 12100 },
    { day: 'Sat', orders: 71, revenue: 18200 },
    { day: 'Sun', orders: 34, revenue: 8500 },
  };

  const mockOrders: Order[] = [
    {
      id: '1',
      orderNumber: 'ORD-2024-001',
      customer: {
        name: 'Rajesh Kumar',
        phone: '+91 98765 43210',
        address: '123, MG Road, Andheri West, Mumbai - 400058',
      },
      items: [
        { name: 'Rice Basmati 1kg', quantity: 2, price: 85.00 },
        { name: 'Dal Toor 500g', quantity: 1, price: 65.00 },
      ],
      totalAmount: 235.00,
      status: 'confirmed',
      createdAt: '2024-12-01T10:30:00Z',
      estimatedDelivery: '2024-12-01T12:00:00Z',
      paymentStatus: 'paid',
      priority: 'normal',
    },
    {
      id: '2',
      orderNumber: 'ORD-2024-002',
      customer: {
        name: 'Priya Sharma',
        phone: '+91 87654 32109',
        address: '456, SV Road, Bandra West, Mumbai - 400050',
      },
      items: [
        { name: 'Atta Wheat 5kg', quantity: 1, price: 245.00 },
        { name: 'Oil Sunflower 1L', quantity: 2, price: 125.00 },
      ],
      totalAmount: 495.00,
      status: 'preparing',
      createdAt: '2024-12-01T11:15:00Z',
      estimatedDelivery: '2024-12-01T13:30:00Z',
      paymentStatus: 'paid',
      priority: 'high',
    },
    {
      id: '3',
      orderNumber: 'ORD-2024-003',
      customer: {
        name: 'Amit Patel',
        phone: '+91 76543 21098',
        address: '789, Hill Road, Bandra West, Mumbai - 400050',
      },
      items: [
        { name: 'Milk 1L', quantity: 3, price: 55.00 },
        { name: 'Bread Brown', quantity: 2, price: 35.00 },
      ],
      totalAmount: 235.00,
      status: 'ready',
      createdAt: '2024-12-01T12:00:00Z',
      estimatedDelivery: '2024-12-01T14:00:00Z',
      paymentStatus: 'paid',
      priority: 'urgent',
    },
  ];

  useEffect(() => {
    setOrders(mockOrders);
    setFilteredOrders(mockOrders);
  }, []);

  useEffect(() => {
    let filtered = orders;

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(order =>
        order.orderNumber.toLowerCase().includes(searchQuery.toLowerCase()) ||
        order.customer.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        order.customer.phone.includes(searchQuery)
      );
    }

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(order => order.status === statusFilter);
    }

    setFilteredOrders(filtered);
  }, [orders, searchQuery, statusFilter]);

  const getStatusColor = (status: Order['status']) => {
    switch (status) {
      case 'placed': return 'bg-gray-100 text-gray-800';
      case 'confirmed': return 'bg-blue-100 text-blue-800';
      case 'preparing': return 'bg-yellow-100 text-yellow-800';
      case 'ready': return 'bg-green-100 text-green-800';
      case 'picked_up': return 'bg-purple-100 text-purple-800';
      case 'delivered': return 'bg-green-100 text-green-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getPriorityColor = (priority: Order['priority']) => {
    switch (priority) {
      case 'urgent': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'normal': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const updateOrderStatus = (orderId: string, newStatus: Order['status']) => {
    setOrders(prevOrders =>
      prevOrders.map(order =>
        order.id === orderId ? { ...order, status: newStatus } : order
      )
    );
  };

  const formatTime = (dateString: string) => {
    return new Date(dateString).toLocaleTimeString('en-IN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const refreshData = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1500);
  };

  return (
    <div className="min-h-screen bg-background p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Merchant Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's what's happening at your store today.
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">This Week</SelectItem>
              <SelectItem value="month">This Month</SelectItem>
            </SelectContent>
          </Select>
          
          <Button variant="outline" onClick={refreshData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Order
          </Button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today's Orders</CardTitle>
            <ShoppingBag className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics.todayOrders}</div>
            <div className="flex items-center space-x-2 mt-2">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <p className="text-xs text-green-600 font-medium">+12% from yesterday</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Today's Revenue</CardTitle>
            <IndianRupee className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₹{metrics.todayRevenue.toLocaleString()}</div>
            <div className="flex items-center space-x-2 mt-2">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <p className="text-xs text-green-600 font-medium">+8.2% from yesterday</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Orders</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">{metrics.pendingOrders}</div>
            <p className="text-xs text-muted-foreground mt-2">
              Requires immediate attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Order Value</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">₹{metrics.averageOrderValue.toFixed(0)}</div>
            <div className="flex items-center space-x-2 mt-2">
              <TrendingDown className="h-4 w-4 text-red-600" />
              <p className="text-xs text-red-600 font-medium">-2.1% from yesterday</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="orders" className="space-y-6">
        <TabsList className="grid w-full max-w-lg grid-cols-4">
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="inventory">Inventory</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="orders" className="space-y-6">
          {/* Orders Management */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Recent Orders</span>
                <div className="flex items-center space-x-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                    <Input
                      placeholder="Search orders..."
                      className="pl-9 w-64"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                  
                  <Select value={statusFilter} onValueChange={setStatusFilter}>
                    <SelectTrigger className="w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Status</SelectItem>
                      <SelectItem value="placed">Placed</SelectItem>
                      <SelectItem value="confirmed">Confirmed</SelectItem>
                      <SelectItem value="preparing">Preparing</SelectItem>
                      <SelectItem value="ready">Ready</SelectItem>
                      <SelectItem value="delivered">Delivered</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {filteredOrders.map((order) => (
                  <Card key={order.id} className="border-l-4 border-l-primary">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="space-y-3 flex-1">
                          <div className="flex items-center space-x-4">
                            <Badge variant="outline" className={getPriorityColor(order.priority)}>
                              {order.priority.toUpperCase()}
                            </Badge>
                            <Badge className={getStatusColor(order.status)}>
                              {order.status.replace('_', ' ').toUpperCase()}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                              {order.orderNumber}
                            </span>
                          </div>
                          
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <div>
                              <h4 className="font-semibold text-lg">{order.customer.name}</h4>
                              <div className="flex items-center space-x-2 mt-1 text-sm text-muted-foreground">
                                <Phone className="h-4 w-4" />
                                <span>{order.customer.phone}</span>
                              </div>
                              <div className="flex items-start space-x-2 mt-1 text-sm text-muted-foreground">
                                <MapPin className="h-4 w-4 mt-0.5" />
                                <span className="leading-tight">{order.customer.address}</span>
                              </div>
                            </div>
                            
                            <div>
                              <div className="flex items-center space-x-4 mb-2">
                                <span className="text-2xl font-bold text-green-600">
                                  ₹{order.totalAmount.toFixed(2)}
                                </span>
                                <Badge variant="outline" className={
                                  order.paymentStatus === 'paid' 
                                    ? 'bg-green-100 text-green-800' 
                                    : order.paymentStatus === 'failed'
                                    ? 'bg-red-100 text-red-800'
                                    : 'bg-yellow-100 text-yellow-800'
                                }>
                                  {order.paymentStatus.toUpperCase()}
                                </Badge>
                              </div>
                              
                              <div className="text-sm text-muted-foreground space-y-1">
                                <div className="flex items-center space-x-2">
                                  <Calendar className="h-4 w-4" />
                                  <span>Ordered at {formatTime(order.createdAt)}</span>
                                </div>
                                {order.estimatedDelivery && (
                                  <div className="flex items-center space-x-2">
                                    <Truck className="h-4 w-4" />
                                    <span>ETA: {formatTime(order.estimatedDelivery)}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <div>
                            <h5 className="font-medium mb-2">Order Items:</h5>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                              {order.items.map((item, index) => (
                                <div key={index} className="flex justify-between items-center p-2 bg-muted rounded">
                                  <span className="text-sm">{item.name}</span>
                                  <div className="text-sm font-medium">
                                    {item.quantity}x ₹{item.price}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex flex-col space-y-2 ml-6">
                          {order.status === 'placed' && (
                            <Button
                              size="sm"
                              onClick={() => updateOrderStatus(order.id, 'confirmed')}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              <CheckCircle className="h-4 w-4 mr-2" />
                              Confirm
                            </Button>
                          )}
                          
                          {order.status === 'confirmed' && (
                            <Button
                              size="sm"
                              onClick={() => updateOrderStatus(order.id, 'preparing')}
                              className="bg-yellow-600 hover:bg-yellow-700"
                            >
                              <Package className="h-4 w-4 mr-2" />
                              Start Preparing
                            </Button>
                          )}
                          
                          {order.status === 'preparing' && (
                            <Button
                              size="sm"
                              onClick={() => updateOrderStatus(order.id, 'ready')}
                              className="bg-green-600 hover:bg-green-700"
                            >
                              <CheckCircle className="h-4 w-4 mr-2" />
                              Mark Ready
                            </Button>
                          )}
                          
                          {order.status === 'ready' && (
                            <Button
                              size="sm"
                              onClick={() => updateOrderStatus(order.id, 'picked_up')}
                              className="bg-purple-600 hover:bg-purple-700"
                            >
                              <Truck className="h-4 w-4 mr-2" />
                              Picked Up
                            </Button>
                          )}
                          
                          <Button variant="outline" size="sm">
                            <Phone className="h-4 w-4 mr-2" />
                            Call Customer
                          </Button>
                          
                          <Button variant="outline" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              
              {filteredOrders.length === 0 && (
                <div className="text-center py-12">
                  <ShoppingBag className="mx-auto h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No orders found</h3>
                  <p className="text-muted-foreground">
                    {searchQuery || statusFilter !== 'all' 
                      ? 'Try adjusting your search or filter criteria'
                      : 'New orders will appear here'
                    }
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {/* Analytics Content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Today's Sales Trend</CardTitle>
                <CardDescription>Orders and revenue by hour</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={salesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stackId="1"
                      stroke="#3b82f6"
                      fill="#3b82f6"
                      fillOpacity={0.6}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Weekly Performance</CardTitle>
                <CardDescription>Last 7 days comparison</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={weeklyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="orders" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="inventory">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <Package className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Inventory Management</h3>
                <p className="text-muted-foreground">Manage your product inventory and stock levels</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <Settings className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Store Settings</h3>
                <p className="text-muted-foreground">Configure your store preferences and business flows</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default MerchantDashboard;
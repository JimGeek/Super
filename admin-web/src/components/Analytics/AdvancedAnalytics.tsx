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
import { DatePickerWithRange } from '@/components/ui/date-picker-with-range';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Progress } from '@/components/ui/progress';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  ComposedChart,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Users,
  ShoppingBag,
  IndianRupee,
  Store,
  Clock,
  Target,
  Eye,
  MousePointer,
  Download,
  Filter,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart as PieChartIcon,
  Activity,
  Calendar,
  MapPin,
  Smartphone,
} from 'lucide-react';

interface MetricCard {
  title: string;
  value: string;
  change: number;
  changeType: 'positive' | 'negative' | 'neutral';
  icon: React.ReactNode;
  description: string;
}

interface ChartData {
  date: string;
  revenue: number;
  orders: number;
  users: number;
  merchants: number;
  conversionRate: number;
  avgOrderValue: number;
}

const AdvancedAnalytics: React.FC = () => {
  const [dateRange, setDateRange] = useState<{ from: Date; to: Date }>({
    from: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    to: new Date(),
  });
  const [selectedVertical, setSelectedVertical] = useState<string>('all');
  const [selectedRegion, setSelectedRegion] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  // Sample data - in real app, this would come from API
  const metricsData: MetricCard[] = [
    {
      title: 'Total Revenue',
      value: '₹12.4M',
      change: 15.3,
      changeType: 'positive',
      icon: <IndianRupee className="h-5 w-5" />,
      description: '+₹1.65M from last month',
    },
    {
      title: 'Active Orders',
      value: '8,247',
      change: 8.2,
      changeType: 'positive',
      icon: <ShoppingBag className="h-5 w-5" />,
      description: '+623 orders this month',
    },
    {
      title: 'Active Users',
      value: '45,892',
      change: 12.5,
      changeType: 'positive',
      icon: <Users className="h-5 w-5" />,
      description: '+5,124 new users',
    },
    {
      title: 'Merchant Partners',
      value: '2,847',
      change: 6.8,
      changeType: 'positive',
      icon: <Store className="h-5 w-5" />,
      description: '+178 new merchants',
    },
    {
      title: 'Avg Order Value',
      value: '₹347',
      change: -2.1,
      changeType: 'negative',
      icon: <Target className="h-5 w-5" />,
      description: '-₹7 from last month',
    },
    {
      title: 'Conversion Rate',
      value: '3.24%',
      change: 4.2,
      changeType: 'positive',
      icon: <MousePointer className="h-5 w-5" />,
      description: '+0.13% improvement',
    },
  ];

  const chartData: ChartData[] = [
    { date: '2024-01', revenue: 850000, orders: 2450, users: 12500, merchants: 180, conversionRate: 2.8, avgOrderValue: 347 },
    { date: '2024-02', revenue: 920000, orders: 2650, users: 13200, merchants: 195, conversionRate: 2.9, avgOrderValue: 347 },
    { date: '2024-03', revenue: 1100000, orders: 3100, users: 15800, merchants: 225, conversionRate: 3.1, avgOrderValue: 355 },
    { date: '2024-04', revenue: 1250000, orders: 3600, users: 18200, merchants: 260, conversionRate: 3.2, avgOrderValue: 347 },
    { date: '2024-05', revenue: 1180000, orders: 3400, users: 19500, merchants: 285, conversionRate: 3.0, avgOrderValue: 347 },
    { date: '2024-06', revenue: 1400000, orders: 4000, users: 22800, merchants: 320, conversionRate: 3.3, avgOrderValue: 350 },
    { date: '2024-07', revenue: 1320000, orders: 3800, users: 24100, merchants: 350, conversionRate: 3.2, avgOrderValue: 347 },
    { date: '2024-08', revenue: 1560000, orders: 4500, users: 28200, merchants: 380, conversionRate: 3.4, avgOrderValue: 347 },
    { date: '2024-09', revenue: 1480000, orders: 4250, users: 31500, merchants: 420, conversionRate: 3.1, avgOrderValue: 348 },
    { date: '2024-10', revenue: 1720000, orders: 4950, users: 35800, merchants: 450, conversionRate: 3.5, avgOrderValue: 347 },
    { date: '2024-11', revenue: 1650000, orders: 4750, users: 38900, merchants: 480, conversionRate: 3.3, avgOrderValue: 347 },
    { date: '2024-12', revenue: 1890000, orders: 5400, users: 42600, merchants: 520, conversionRate: 3.6, avgOrderValue: 350 },
  ];

  const verticalData = [
    { name: 'Kirana', value: 35, orders: 2890, revenue: 8420000 },
    { name: 'Beauty', value: 22, orders: 1780, revenue: 5200000 },
    { name: 'Auto Care', value: 18, orders: 1450, revenue: 4100000 },
    { name: 'Pharmacy', value: 12, orders: 970, revenue: 2800000 },
    { name: 'Electronics', value: 8, orders: 650, revenue: 1900000 },
    { name: 'Others', value: 5, orders: 410, revenue: 1200000 },
  ];

  const regionData = [
    { name: 'Mumbai', users: 12500, merchants: 450, revenue: 4200000, growth: 15.2 },
    { name: 'Delhi', users: 10800, merchants: 380, revenue: 3800000, growth: 12.8 },
    { name: 'Bangalore', users: 9200, merchants: 320, revenue: 3200000, growth: 18.5 },
    { name: 'Chennai', users: 7600, merchants: 280, revenue: 2600000, growth: 14.2 },
    { name: 'Pune', users: 6800, merchants: 250, revenue: 2200000, growth: 16.8 },
    { name: 'Hyderabad', users: 5400, merchants: 200, revenue: 1800000, growth: 13.5 },
  ];

  const cohortData = [
    { month: 'Jan', retention1: 100, retention2: 85, retention3: 72, retention4: 65, retention5: 58, retention6: 52 },
    { month: 'Feb', retention1: 100, retention2: 88, retention3: 75, retention4: 68, retention5: 61, retention6: 55 },
    { month: 'Mar', retention1: 100, retention2: 82, retention3: 69, retention4: 62, retention5: 55, retention6: 49 },
    { month: 'Apr', retention1: 100, retention2: 90, retention3: 78, retention4: 71, retention5: 64, retention6: 58 },
    { month: 'May', retention1: 100, retention2: 86, retention3: 73, retention4: 66, retention5: 59, retention6: null },
    { month: 'Jun', retention1: 100, retention2: 92, retention3: 80, retention4: 73, retention5: null, retention6: null },
  ];

  const funnelData = [
    { stage: 'App Opens', users: 45892, percentage: 100, color: '#3b82f6' },
    { stage: 'Browsed Products', users: 32124, percentage: 70, color: '#10b981' },
    { stage: 'Added to Cart', users: 18456, percentage: 40, color: '#f59e0b' },
    { stage: 'Started Checkout', users: 9228, percentage: 20, color: '#ef4444' },
    { stage: 'Completed Order', users: 5537, percentage: 12, color: '#8b5cf6' },
  ];

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'];

  const refreshData = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1500);
  };

  return (
    <div className="p-6 space-y-6 bg-background">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Advanced Analytics</h1>
          <p className="text-muted-foreground">
            Comprehensive insights into platform performance and user behavior
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            onClick={refreshData}
            disabled={isLoading}
            className="flex items-center space-x-2"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </Button>
          
          <Button className="flex items-center space-x-2">
            <Download className="h-4 w-4" />
            <span>Export Report</span>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filters</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-48">
            <label className="text-sm font-medium mb-2 block">Date Range</label>
            <DatePickerWithRange />
          </div>
          
          <div className="flex-1 min-w-48">
            <label className="text-sm font-medium mb-2 block">Business Vertical</label>
            <Select value={selectedVertical} onValueChange={setSelectedVertical}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Verticals</SelectItem>
                <SelectItem value="kirana">Kirana Stores</SelectItem>
                <SelectItem value="beauty">Beauty Salons</SelectItem>
                <SelectItem value="auto">Auto Care</SelectItem>
                <SelectItem value="pharmacy">Pharmacy</SelectItem>
                <SelectItem value="electronics">Electronics</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex-1 min-w-48">
            <label className="text-sm font-medium mb-2 block">Region</label>
            <Select value={selectedRegion} onValueChange={setSelectedRegion}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Regions</SelectItem>
                <SelectItem value="mumbai">Mumbai</SelectItem>
                <SelectItem value="delhi">Delhi</SelectItem>
                <SelectItem value="bangalore">Bangalore</SelectItem>
                <SelectItem value="chennai">Chennai</SelectItem>
                <SelectItem value="pune">Pune</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {metricsData.map((metric, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{metric.title}</CardTitle>
              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                {metric.icon}
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
              <div className="flex items-center space-x-2 mt-2">
                {metric.changeType === 'positive' ? (
                  <TrendingUp className="h-4 w-4 text-green-600" />
                ) : metric.changeType === 'negative' ? (
                  <TrendingDown className="h-4 w-4 text-red-600" />
                ) : (
                  <Activity className="h-4 w-4 text-gray-600" />
                )}
                <span className={`text-sm font-medium ${
                  metric.changeType === 'positive' ? 'text-green-600' :
                  metric.changeType === 'negative' ? 'text-red-600' :
                  'text-gray-600'
                }`}>
                  {metric.change > 0 ? '+' : ''}{metric.change}%
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {metric.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Analytics Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full max-w-2xl grid-cols-6">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="revenue">Revenue</TabsTrigger>
          <TabsTrigger value="users">Users</TabsTrigger>
          <TabsTrigger value="merchants">Merchants</TabsTrigger>
          <TabsTrigger value="conversion">Conversion</TabsTrigger>
          <TabsTrigger value="regions">Regions</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue Trend */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BarChart3 className="h-5 w-5" />
                  <span>Revenue Trend</span>
                </CardTitle>
                <CardDescription>Monthly revenue performance</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip formatter={(value: any) => [`₹${value.toLocaleString()}`, 'Revenue']} />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="#3b82f6"
                      fill="url(#colorRevenue)"
                      strokeWidth={2}
                    />
                    <defs>
                      <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Orders & Users */}
            <Card>
              <CardHeader>
                <CardTitle>Orders vs Users Growth</CardTitle>
                <CardDescription>Monthly comparison</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="orders" fill="#10b981" name="Orders" />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="users"
                      stroke="#f59e0b"
                      strokeWidth={3}
                      name="Users"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Business Verticals */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <PieChartIcon className="h-5 w-5" />
                  <span>Business Verticals</span>
                </CardTitle>
                <CardDescription>Revenue distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={verticalData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {verticalData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value: any) => [`${value}%`, 'Share']} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* User Acquisition Funnel */}
            <Card>
              <CardHeader>
                <CardTitle>Conversion Funnel</CardTitle>
                <CardDescription>User acquisition journey</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {funnelData.map((stage, index) => (
                    <div key={index} className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>{stage.stage}</span>
                        <span className="font-medium">{stage.users.toLocaleString()}</span>
                      </div>
                      <Progress value={stage.percentage} className="h-3" />
                      <div className="text-xs text-muted-foreground text-right">
                        {stage.percentage}% conversion
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Top Performing Regions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <MapPin className="h-5 w-5" />
                  <span>Top Regions</span>
                </CardTitle>
                <CardDescription>Performance by city</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-64">
                  <div className="space-y-4">
                    {regionData.map((region, index) => (
                      <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{region.name}</div>
                          <div className="text-sm text-muted-foreground">
                            {region.users.toLocaleString()} users • {region.merchants} merchants
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">₹{(region.revenue / 1000000).toFixed(1)}M</div>
                          <div className="flex items-center space-x-1 text-sm text-green-600">
                            <TrendingUp className="h-3 w-3" />
                            <span>{region.growth}%</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="revenue" className="space-y-6">
          {/* Revenue analytics content */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Revenue by Time of Day</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={[
                    { hour: '6AM', revenue: 45000 },
                    { hour: '9AM', revenue: 125000 },
                    { hour: '12PM', revenue: 180000 },
                    { hour: '3PM', revenue: 220000 },
                    { hour: '6PM', revenue: 280000 },
                    { hour: '9PM', revenue: 190000 },
                    { hour: '12AM', revenue: 85000 },
                  ]}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip formatter={(value: any) => [`₹${value.toLocaleString()}`, 'Revenue']} />
                    <Bar dataKey="revenue" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Revenue Goals</CardTitle>
                <CardDescription>Monthly targets vs actual</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="revenue"
                      stroke="#10b981"
                      strokeWidth={2}
                      name="Actual Revenue"
                    />
                    <ReferenceLine y={1500000} stroke="#ef4444" strokeDasharray="5 5" label="Target" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Additional tab contents would go here */}
        <TabsContent value="users" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>User Retention Cohorts</CardTitle>
              <CardDescription>Monthly cohort retention analysis</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      <th className="border p-2 text-left">Cohort</th>
                      <th className="border p-2 text-center">Month 1</th>
                      <th className="border p-2 text-center">Month 2</th>
                      <th className="border p-2 text-center">Month 3</th>
                      <th className="border p-2 text-center">Month 4</th>
                      <th className="border p-2 text-center">Month 5</th>
                      <th className="border p-2 text-center">Month 6</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cohortData.map((cohort, index) => (
                      <tr key={index}>
                        <td className="border p-2 font-medium">{cohort.month}</td>
                        <td className="border p-2 text-center bg-green-100">{cohort.retention1}%</td>
                        <td className="border p-2 text-center" style={{
                          backgroundColor: `rgba(34, 197, 94, ${cohort.retention2 / 100})`
                        }}>{cohort.retention2}%</td>
                        <td className="border p-2 text-center" style={{
                          backgroundColor: `rgba(34, 197, 94, ${cohort.retention3 / 100})`
                        }}>{cohort.retention3}%</td>
                        <td className="border p-2 text-center" style={{
                          backgroundColor: `rgba(34, 197, 94, ${cohort.retention4 / 100})`
                        }}>{cohort.retention4}%</td>
                        <td className="border p-2 text-center" style={{
                          backgroundColor: cohort.retention5 ? `rgba(34, 197, 94, ${cohort.retention5 / 100})` : '#f3f4f6'
                        }}>{cohort.retention5 ? `${cohort.retention5}%` : '-'}</td>
                        <td className="border p-2 text-center" style={{
                          backgroundColor: cohort.retention6 ? `rgba(34, 197, 94, ${cohort.retention6 / 100})` : '#f3f4f6'
                        }}>{cohort.retention6 ? `${cohort.retention6}%` : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Placeholder for other tabs */}
        <TabsContent value="merchants">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <Store className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Merchant Analytics</h3>
                <p className="text-muted-foreground">Detailed merchant performance metrics coming soon</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="conversion">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <Target className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Conversion Analytics</h3>
                <p className="text-muted-foreground">Advanced conversion tracking and optimization metrics</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="regions">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center py-8">
                <MapPin className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">Regional Analytics</h3>
                <p className="text-muted-foreground">Geographic performance and expansion insights</p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default AdvancedAnalytics;
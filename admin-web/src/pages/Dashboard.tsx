import React from 'react'
import { useQuery } from 'react-query'
import { 
  TrendingUp, 
  Users, 
  ShoppingCart, 
  DollarSign,
  AlertCircle,
  CheckCircle
} from 'lucide-react'
import StatsCard from '../components/StatsCard'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

// Mock data - in production, this would come from your API
const mockStats = {
  totalRevenue: 125000,
  totalOrders: 1250,
  activeMerchants: 45,
  successRate: 94.5,
}

const mockChartData = [
  { name: 'Jan', revenue: 12000, orders: 120 },
  { name: 'Feb', revenue: 15000, orders: 150 },
  { name: 'Mar', revenue: 18000, orders: 180 },
  { name: 'Apr', revenue: 22000, orders: 220 },
  { name: 'May', revenue: 25000, orders: 250 },
  { name: 'Jun', revenue: 30000, orders: 300 },
]

const mockRecentOrders = [
  { id: '1', customer: 'Rahul Sharma', merchant: 'Raj Kirana Store', amount: 450, status: 'completed' },
  { id: '2', customer: 'Priya Patel', merchant: 'Style Cut Salon', amount: 800, status: 'in_progress' },
  { id: '3', customer: 'Amit Kumar', merchant: 'AutoCare Garage', amount: 2500, status: 'confirmed' },
  { id: '4', customer: 'Sneha Singh', merchant: 'Fresh Mart', amount: 320, status: 'completed' },
  { id: '5', customer: 'Rajesh Gupta', merchant: 'AquaPure Solutions', amount: 1200, status: 'pending' },
]

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'completed':
      return <span className="badge-success">Completed</span>
    case 'in_progress':
      return <span className="badge-warning">In Progress</span>
    case 'confirmed':
      return <span className="badge badge-blue-100 text-blue-800">Confirmed</span>
    case 'pending':
      return <span className="badge-gray">Pending</span>
    default:
      return <span className="badge-gray">{status}</span>
  }
}

export default function Dashboard() {
  const { data: stats, isLoading } = useQuery('dashboard-stats', 
    () => Promise.resolve(mockStats),
    { refetchInterval: 30000 }
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="min-w-0 flex-1">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:truncate sm:text-3xl">
            Dashboard
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Welcome to SUPER Admin Dashboard
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatsCard
          title="Total Revenue"
          value={`₹${stats?.totalRevenue.toLocaleString()}`}
          icon={DollarSign}
          trend={{ value: 12, isPositive: true }}
          color="green"
        />
        <StatsCard
          title="Total Orders"
          value={stats?.totalOrders.toLocaleString()}
          icon={ShoppingCart}
          trend={{ value: 8, isPositive: true }}
          color="blue"
        />
        <StatsCard
          title="Active Merchants"
          value={stats?.activeMerchants}
          icon={Users}
          trend={{ value: 3, isPositive: true }}
          color="purple"
        />
        <StatsCard
          title="Success Rate"
          value={`${stats?.successRate}%`}
          icon={TrendingUp}
          trend={{ value: 2, isPositive: true }}
          color="green"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Revenue Chart */}
        <div className="card">
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Revenue Trend</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Revenue']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Orders Chart */}
        <div className="card">
          <div className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Orders Trend</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={mockChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value: number) => [value.toLocaleString(), 'Orders']}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="orders" 
                    stroke="#10b981" 
                    strokeWidth={2}
                    dot={{ fill: '#10b981' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Orders */}
      <div className="card">
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">Recent Orders</h3>
            <a href="/orders" className="text-sm text-primary-600 hover:text-primary-700">
              View all
            </a>
          </div>
          <div className="overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Merchant
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockRecentOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {order.customer}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {order.merchant}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{order.amount.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(order.status)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* System Alerts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card">
          <div className="p-6">
            <div className="flex items-center mb-4">
              <CheckCircle className="h-5 w-5 text-green-500 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">System Status</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">UPI Gateway</span>
                <span className="badge-success">Online</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Payment Processing</span>
                <span className="badge-success">Healthy</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Order Processing</span>
                <span className="badge-success">Normal</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">Notification Service</span>
                <span className="badge-warning">Degraded</span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="p-6">
            <div className="flex items-center mb-4">
              <AlertCircle className="h-5 w-5 text-orange-500 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">Recent Alerts</h3>
            </div>
            <div className="space-y-3">
              <div className="text-sm">
                <p className="text-gray-900">High payment failure rate detected</p>
                <p className="text-gray-500 text-xs">2 minutes ago</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-900">New merchant verification pending</p>
                <p className="text-gray-500 text-xs">1 hour ago</p>
              </div>
              <div className="text-sm">
                <p className="text-gray-900">Server maintenance scheduled</p>
                <p className="text-gray-500 text-xs">3 hours ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
import React, { useState } from 'react'
import { useQuery } from 'react-query'
import { 
  Search, 
  Filter, 
  Eye,
  MoreHorizontal,
  Package,
  Clock,
  CheckCircle,
  XCircle,
  Truck
} from 'lucide-react'

// Mock data - in production, this would come from your API
const mockOrders = [
  {
    id: '1',
    orderNumber: 'KIRAN20241201001',
    customer: {
      name: 'Rahul Sharma',
      phone: '+919876543230'
    },
    merchant: {
      name: 'Raj Kirana Store',
      type: 'kirana'
    },
    amount: 561.00,
    status: 'completed',
    orderType: 'delivery',
    createdAt: '2024-12-01T10:30:00Z',
    items: ['Basmati Rice', 'Toor Dal'],
    paymentStatus: 'paid'
  },
  {
    id: '2',
    orderNumber: 'SALON20241201001', 
    customer: {
      name: 'Priya Patel',
      phone: '+919876543231'
    },
    merchant: {
      name: 'Style Cut Salon',
      type: 'barber'
    },
    amount: 944.00,
    status: 'completed',
    orderType: 'in_store_appointment',
    createdAt: '2024-12-01T09:15:00Z',
    items: ['Hair Cut & Styling', 'Hair Spa Treatment'],
    paymentStatus: 'paid'
  },
  {
    id: '3',
    orderNumber: 'GARAGE20241201001',
    customer: {
      name: 'Amit Kumar', 
      phone: '+919876543232'
    },
    merchant: {
      name: 'AutoCare Garage',
      type: 'garage'
    },
    amount: 3150.00,
    status: 'confirmed',
    orderType: 'at_home_service',
    createdAt: '2024-12-01T11:45:00Z',
    items: ['Car Service (Full)', 'Engine Oil'],
    paymentStatus: 'pending'
  },
  {
    id: '4',
    orderNumber: 'FRESH20241201001',
    customer: {
      name: 'Sneha Singh',
      phone: '+919876543233'
    },
    merchant: {
      name: 'Fresh Mart Grocery',
      type: 'grocery'
    },
    amount: 320.00,
    status: 'in_transit',
    orderType: 'delivery',
    createdAt: '2024-12-01T12:20:00Z',
    items: ['Fruits & Vegetables', 'Dairy Products'],
    paymentStatus: 'paid'
  },
  {
    id: '5',
    orderNumber: 'AQUA20241201001',
    customer: {
      name: 'Rajesh Gupta',
      phone: '+919876543234'
    },
    merchant: {
      name: 'AquaPure Solutions',
      type: 'water_purifier'
    },
    amount: 1200.00,
    status: 'placed',
    orderType: 'delivery',
    createdAt: '2024-12-01T13:10:00Z',
    items: ['Water Purifier Installation'],
    paymentStatus: 'paid'
  }
]

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center badge-success">
          <CheckCircle className="w-3 h-3 mr-1" />
          Completed
        </span>
      )
    case 'in_transit':
      return (
        <span className="inline-flex items-center badge bg-blue-100 text-blue-800">
          <Truck className="w-3 h-3 mr-1" />
          In Transit
        </span>
      )
    case 'confirmed':
      return (
        <span className="inline-flex items-center badge bg-purple-100 text-purple-800">
          <CheckCircle className="w-3 h-3 mr-1" />
          Confirmed
        </span>
      )
    case 'placed':
      return (
        <span className="inline-flex items-center badge-warning">
          <Clock className="w-3 h-3 mr-1" />
          Placed
        </span>
      )
    case 'cancelled':
      return (
        <span className="inline-flex items-center badge-danger">
          <XCircle className="w-3 h-3 mr-1" />
          Cancelled
        </span>
      )
    default:
      return <span className="badge-gray">{status}</span>
  }
}

const getPaymentStatusBadge = (status: string) => {
  switch (status) {
    case 'paid':
      return <span className="badge-success">Paid</span>
    case 'pending':
      return <span className="badge-warning">Pending</span>
    case 'failed':
      return <span className="badge-danger">Failed</span>
    case 'refunded':
      return <span className="badge-gray">Refunded</span>
    default:
      return <span className="badge-gray">{status}</span>
  }
}

const getOrderTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    delivery: 'Delivery',
    pickup: 'Pickup',
    at_home_service: 'At-Home Service',
    in_store_appointment: 'In-Store Appointment'
  }
  return labels[type] || type
}

export default function Orders() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedOrder, setSelectedOrder] = useState<string | null>(null)

  const { data: orders, isLoading, refetch } = useQuery(
    ['orders', searchTerm, statusFilter],
    () => {
      // Simulate API call
      let filtered = mockOrders
      
      if (searchTerm) {
        filtered = filtered.filter(order => 
          order.orderNumber.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.merchant.name.toLowerCase().includes(searchTerm.toLowerCase())
        )
      }
      
      if (statusFilter !== 'all') {
        filtered = filtered.filter(order => order.status === statusFilter)
      }
      
      return Promise.resolve(filtered)
    },
    { refetchInterval: 30000 }
  )

  const handleStatusChange = async (orderId: string, newStatus: string) => {
    // In production, this would call your API
    console.log(`Changing order ${orderId} status to ${newStatus}`)
    refetch()
  }

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
            Orders
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Monitor and manage all platform orders
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">Total Orders</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {orders?.length || 0}
                </p>
              </div>
              <div className="text-blue-600">
                <Package className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>
        
        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">Completed</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {orders?.filter(o => o.status === 'completed').length || 0}
                </p>
              </div>
              <div className="text-green-600">
                <CheckCircle className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">In Progress</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {orders?.filter(o => ['placed', 'confirmed', 'in_transit'].includes(o.status)).length || 0}
                </p>
              </div>
              <div className="text-orange-600">
                <Clock className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">Total Value</p>
                <p className="text-2xl font-semibold text-gray-900">
                  ₹{orders?.reduce((sum, o) => sum + o.amount, 0).toLocaleString() || 0}
                </p>
              </div>
              <div className="text-purple-600">
                <Package className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="p-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search orders..."
                className="form-input pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="relative">
              <Filter className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <select
                className="form-input pl-10 appearance-none"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="all">All Status</option>
                <option value="placed">Placed</option>
                <option value="confirmed">Confirmed</option>
                <option value="in_transit">In Transit</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            <button className="btn-secondary">
              <Filter className="w-4 h-4 mr-2" />
              More Filters
            </button>
          </div>
        </div>
      </div>

      {/* Orders Table */}
      <div className="card">
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Order
                </th>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Payment
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {orders?.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {order.orderNumber}
                      </div>
                      <div className="text-sm text-gray-500">
                        {new Date(order.createdAt).toLocaleDateString()} at{' '}
                        {new Date(order.createdAt).toLocaleTimeString()}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        Items: {order.items.join(', ')}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {order.customer.name}
                    </div>
                    <div className="text-sm text-gray-500">
                      {order.customer.phone}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">
                      {order.merchant.name}
                    </div>
                    <div className="text-sm text-gray-500 capitalize">
                      {order.merchant.type.replace('_', ' ')}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ₹{order.amount.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(order.status)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getPaymentStatusBadge(order.paymentStatus)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {getOrderTypeLabel(order.orderType)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        className="text-primary-600 hover:text-primary-900"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <div className="relative">
                        <button
                          className="text-gray-600 hover:text-gray-900"
                          onClick={() => setSelectedOrder(
                            selectedOrder === order.id ? null : order.id
                          )}
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                        {selectedOrder === order.id && (
                          <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border">
                            <div className="py-1">
                              {order.status === 'placed' && (
                                <button
                                  className="block px-4 py-2 text-sm text-green-700 hover:bg-green-50 w-full text-left"
                                  onClick={() => handleStatusChange(order.id, 'confirmed')}
                                >
                                  Confirm Order
                                </button>
                              )}
                              {order.status === 'confirmed' && (
                                <button
                                  className="block px-4 py-2 text-sm text-blue-700 hover:bg-blue-50 w-full text-left"
                                  onClick={() => handleStatusChange(order.id, 'in_transit')}
                                >
                                  Mark In Transit
                                </button>
                              )}
                              {order.status === 'in_transit' && (
                                <button
                                  className="block px-4 py-2 text-sm text-green-700 hover:bg-green-50 w-full text-left"
                                  onClick={() => handleStatusChange(order.id, 'completed')}
                                >
                                  Mark Completed
                                </button>
                              )}
                              <button className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
                                View Timeline
                              </button>
                              <button className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
                                Contact Customer
                              </button>
                              {['placed', 'confirmed'].includes(order.status) && (
                                <button
                                  className="block px-4 py-2 text-sm text-red-700 hover:bg-red-50 w-full text-left"
                                  onClick={() => handleStatusChange(order.id, 'cancelled')}
                                >
                                  Cancel Order
                                </button>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <p className="text-sm text-gray-700">
            Showing <span className="font-medium">1</span> to{' '}
            <span className="font-medium">{orders?.length || 0}</span> of{' '}
            <span className="font-medium">{orders?.length || 0}</span> results
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button className="btn-secondary">Previous</button>
          <button className="btn-secondary">Next</button>
        </div>
      </div>
    </div>
  )
}
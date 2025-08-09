import React, { useState } from 'react'
import { useQuery } from 'react-query'
import { 
  Plus, 
  Search, 
  Filter, 
  MoreHorizontal,
  Eye,
  Edit,
  Ban,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react'

// Mock data - in production, this would come from your API
const mockMerchants = [
  {
    id: '1',
    name: 'Raj Kirana Store',
    businessType: 'kirana',
    email: 'raj@rajkirana.com',
    phone: '+919876543210',
    city: 'Mumbai',
    status: 'active',
    revenue: 45000,
    orders: 234,
    rating: 4.8,
    joinedDate: '2024-01-15'
  },
  {
    id: '2', 
    name: 'Style Cut Salon',
    businessType: 'barber',
    email: 'info@stylecutsalon.com',
    phone: '+919876543211',
    city: 'Mumbai',
    status: 'active',
    revenue: 32000,
    orders: 156,
    rating: 4.6,
    joinedDate: '2024-02-01'
  },
  {
    id: '3',
    name: 'AutoCare Garage',
    businessType: 'garage', 
    email: 'service@autocare.com',
    phone: '+919876543212',
    city: 'Mumbai',
    status: 'pending',
    revenue: 0,
    orders: 0,
    rating: 0,
    joinedDate: '2024-03-10'
  },
  {
    id: '4',
    name: 'AquaPure Solutions',
    businessType: 'water_purifier',
    email: 'sales@aquapure.com', 
    phone: '+919876543213',
    city: 'Mumbai',
    status: 'suspended',
    revenue: 15000,
    orders: 45,
    rating: 3.2,
    joinedDate: '2024-01-20'
  },
  {
    id: '5',
    name: 'Fresh Mart Grocery',
    businessType: 'grocery',
    email: 'manager@freshmart.com',
    phone: '+919876543214', 
    city: 'Mumbai',
    status: 'active',
    revenue: 67000,
    orders: 389,
    rating: 4.9,
    joinedDate: '2024-01-05'
  }
]

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'active':
      return (
        <span className="inline-flex items-center badge-success">
          <CheckCircle className="w-3 h-3 mr-1" />
          Active
        </span>
      )
    case 'pending':
      return (
        <span className="inline-flex items-center badge-warning">
          <Clock className="w-3 h-3 mr-1" />
          Pending
        </span>
      )
    case 'suspended':
      return (
        <span className="inline-flex items-center badge-danger">
          <XCircle className="w-3 h-3 mr-1" />
          Suspended
        </span>
      )
    case 'inactive':
      return (
        <span className="inline-flex items-center badge-gray">
          <Ban className="w-3 h-3 mr-1" />
          Inactive
        </span>
      )
    default:
      return <span className="badge-gray">{status}</span>
  }
}

const getBusinessTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    kirana: 'Kirana Store',
    barber: 'Barber/Salon',
    garage: 'Auto Service',
    water_purifier: 'Water Purifier', 
    grocery: 'Grocery',
    restaurant: 'Restaurant',
    pharmacy: 'Pharmacy',
    electronics: 'Electronics'
  }
  return labels[type] || type
}

export default function Merchants() {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedMerchant, setSelectedMerchant] = useState<string | null>(null)

  const { data: merchants, isLoading, refetch } = useQuery(
    ['merchants', searchTerm, statusFilter],
    () => {
      // Simulate API call
      let filtered = mockMerchants
      
      if (searchTerm) {
        filtered = filtered.filter(merchant => 
          merchant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          merchant.email.toLowerCase().includes(searchTerm.toLowerCase())
        )
      }
      
      if (statusFilter !== 'all') {
        filtered = filtered.filter(merchant => merchant.status === statusFilter)
      }
      
      return Promise.resolve(filtered)
    },
    { refetchInterval: 30000 }
  )

  const handleStatusChange = async (merchantId: string, newStatus: string) => {
    // In production, this would call your API
    console.log(`Changing merchant ${merchantId} status to ${newStatus}`)
    // Refetch data
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
            Merchants
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Manage merchant onboarding and operations
          </p>
        </div>
        <div className="mt-4 flex md:ml-4 md:mt-0">
          <button className="btn-primary">
            <Plus className="w-4 h-4 mr-2" />
            Add Merchant
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">Total Merchants</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {merchants?.length || 0}
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
                <p className="text-sm font-medium text-gray-500">Active Merchants</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {merchants?.filter(m => m.status === 'active').length || 0}
                </p>
              </div>
              <div className="text-blue-600">
                <CheckCircle className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="p-6">
            <div className="flex items-center">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-500">Pending Approval</p>
                <p className="text-2xl font-semibold text-gray-900">
                  {merchants?.filter(m => m.status === 'pending').length || 0}
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
                <p className="text-sm font-medium text-gray-500">Total Revenue</p>
                <p className="text-2xl font-semibold text-gray-900">
                  ₹{merchants?.reduce((sum, m) => sum + m.revenue, 0).toLocaleString() || 0}
                </p>
              </div>
              <div className="text-green-600">
                <CheckCircle className="w-8 h-8" />
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
                placeholder="Search merchants..."
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
                <option value="active">Active</option>
                <option value="pending">Pending</option>
                <option value="suspended">Suspended</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>

            <button className="btn-secondary">
              <Filter className="w-4 h-4 mr-2" />
              More Filters
            </button>
          </div>
        </div>
      </div>

      {/* Merchants Table */}
      <div className="card">
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Merchant
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Business Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Revenue
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Orders
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Rating
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {merchants?.map((merchant) => (
                <tr key={merchant.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        <div className="h-10 w-10 rounded-full bg-primary-100 flex items-center justify-center">
                          <span className="text-sm font-medium text-primary-600">
                            {merchant.name.charAt(0)}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {merchant.name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {merchant.email}
                        </div>
                        <div className="text-xs text-gray-400">
                          {merchant.city} • {merchant.phone}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {getBusinessTypeLabel(merchant.businessType)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(merchant.status)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ₹{merchant.revenue.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {merchant.orders.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex items-center">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <svg
                            key={star}
                            className={`w-4 h-4 ${
                              star <= merchant.rating
                                ? 'text-yellow-400'
                                : 'text-gray-300'
                            }`}
                            fill="currentColor"
                            viewBox="0 0 20 20"
                          >
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        ))}
                      </div>
                      <span className="ml-1 text-sm text-gray-500">
                        ({merchant.rating.toFixed(1)})
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center space-x-2">
                      <button
                        className="text-primary-600 hover:text-primary-900"
                        title="View Details"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        className="text-gray-600 hover:text-gray-900"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <div className="relative">
                        <button
                          className="text-gray-600 hover:text-gray-900"
                          onClick={() => setSelectedMerchant(
                            selectedMerchant === merchant.id ? null : merchant.id
                          )}
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                        {selectedMerchant === merchant.id && (
                          <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 border">
                            <div className="py-1">
                              {merchant.status === 'pending' && (
                                <button
                                  className="block px-4 py-2 text-sm text-green-700 hover:bg-green-50 w-full text-left"
                                  onClick={() => handleStatusChange(merchant.id, 'active')}
                                >
                                  Approve Merchant
                                </button>
                              )}
                              {merchant.status === 'active' && (
                                <button
                                  className="block px-4 py-2 text-sm text-red-700 hover:bg-red-50 w-full text-left"
                                  onClick={() => handleStatusChange(merchant.id, 'suspended')}
                                >
                                  Suspend Merchant
                                </button>
                              )}
                              {merchant.status === 'suspended' && (
                                <button
                                  className="block px-4 py-2 text-sm text-green-700 hover:bg-green-50 w-full text-left"
                                  onClick={() => handleStatusChange(merchant.id, 'active')}
                                >
                                  Reactivate Merchant
                                </button>
                              )}
                              <button className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
                                View Analytics
                              </button>
                              <button className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 w-full text-left">
                                Contact Merchant
                              </button>
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
            <span className="font-medium">{merchants?.length || 0}</span> of{' '}
            <span className="font-medium">{merchants?.length || 0}</span> results
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
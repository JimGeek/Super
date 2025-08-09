import React from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CreditCard, IndianRupee, QrCode, Smartphone, RefreshCw } from 'lucide-react';

interface PaymentNodeData {
  label: string;
  paymentType: 'upi_collect' | 'upi_intent' | 'qr_code' | 'mandate' | 'refund';
  description?: string;
  config: {
    amount?: number;
    currency?: string;
    description?: string;
    expiryTime?: string;
    recurringType?: 'monthly' | 'weekly' | 'daily';
    maxAmount?: number;
  };
}

const paymentIcons = {
  upi_collect: Smartphone,
  upi_intent: CreditCard,
  qr_code: QrCode,
  mandate: RefreshCw,
  refund: IndianRupee,
};

const paymentColors = {
  upi_collect: 'bg-blue-100 text-blue-600',
  upi_intent: 'bg-green-100 text-green-600',
  qr_code: 'bg-purple-100 text-purple-600',
  mandate: 'bg-orange-100 text-orange-600',
  refund: 'bg-red-100 text-red-600',
};

const PaymentNode: React.FC<NodeProps<PaymentNodeData>> = ({ data, selected }) => {
  const Icon = paymentIcons[data.paymentType] || CreditCard;
  const colorClass = paymentColors[data.paymentType] || 'bg-gray-100 text-gray-600';
  
  return (
    <Card className={`min-w-64 shadow-sm border-2 transition-all ${
      selected 
        ? 'border-primary shadow-lg' 
        : 'border-lime-200 hover:border-lime-300'
    }`}>
      <CardContent className="p-3">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 border-2 border-lime-400 bg-white"
        />
        
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${colorClass}`}>
              <Icon className="w-5 h-5" />
            </div>
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-gray-900">
              {data.label || 'Payment'}
            </h3>
            
            <Badge variant="outline" className="mt-1 text-xs">
              {data.paymentType.replace('_', ' ').toUpperCase()}
            </Badge>
            
            {data.description && (
              <p className="text-xs text-gray-500 mt-2">
                {data.description}
              </p>
            )}
            
            {/* Payment Configuration */}
            {data.config && (
              <div className="mt-3 space-y-2">
                {/* Amount */}
                {data.config.amount && (
                  <div className="flex items-center justify-between p-2 bg-green-50 rounded-lg">
                    <span className="text-xs text-gray-600">Amount</span>
                    <div className="flex items-center space-x-1">
                      <IndianRupee className="w-3 h-3 text-green-600" />
                      <span className="font-semibold text-sm text-green-700">
                        {data.config.amount.toFixed(2)}
                      </span>
                    </div>
                  </div>
                )}
                
                {/* Max Amount for Mandates */}
                {data.config.maxAmount && data.paymentType === 'mandate' && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Max Amount</span>
                    <span className="font-medium">₹{data.config.maxAmount}</span>
                  </div>
                )}
                
                {/* Recurring Type for Mandates */}
                {data.config.recurringType && data.paymentType === 'mandate' && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Frequency</span>
                    <Badge variant="secondary" className="text-xs">
                      {data.config.recurringType}
                    </Badge>
                  </div>
                )}
                
                {/* Payment Description */}
                {data.config.description && (
                  <div className="text-xs">
                    <span className="text-gray-500">Description:</span>
                    <div className="mt-1 bg-gray-50 rounded px-2 py-1 text-xs truncate">
                      {data.config.description}
                    </div>
                  </div>
                )}
                
                {/* Expiry Time */}
                {data.config.expiryTime && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Expires</span>
                    <span className="font-medium">{data.config.expiryTime}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* Success/Failure Handles for Payment Nodes */}
        <div className="flex justify-between items-center mt-3 pt-2 border-t border-gray-100">
          <div className="text-xs text-green-600 font-medium">Success</div>
          <div className="text-xs text-red-600 font-medium">Failed</div>
        </div>
        
        <Handle
          type="source"
          position={Position.Bottom}
          id="success"
          style={{ left: '25%', background: '#10b981' }}
          className="w-3 h-3 border-2 border-green-400"
        />
        
        <Handle
          type="source"
          position={Position.Bottom}
          id="failed"
          style={{ left: '75%', background: '#ef4444' }}
          className="w-3 h-3 border-2 border-red-400"
        />
      </CardContent>
    </Card>
  );
};

export default PaymentNode;
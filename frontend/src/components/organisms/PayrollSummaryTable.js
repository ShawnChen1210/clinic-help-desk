import React from 'react';
import {useDateFormatter} from "../../hooks/useDateFormatter";
export default function PayrollSummaryTable({ payrollData, companyInfo, className = "" }) {
  const { formatDateString } = useDateFormatter()
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
      minimumFractionDigits: 2
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-CA');
  };

  return (
    <div className={`bg-white border border-gray-300 ${className}`}>
      {/* Company Header */}
      <div className="border-b border-gray-300 p-4 bg-gray-50">
        <h1 className="text-lg font-bold text-gray-900">
          {companyInfo?.name || 'Alternative Therapy On the Go Inc.'}
        </h1>
        <p className="text-sm text-gray-600">
          {companyInfo?.address || '23 - 7330 122nd Street, Surrey, BC V3W 1B4'}
        </p>
        <div className="flex justify-between items-center mt-2">
          <span className="text-sm font-medium">Pay period ending</span>
          <span className="text-sm">{formatDateString(payrollData.pay_period_end)}</span>
        </div>
      </div>

      {/* Employee Info */}
      <div className="border-b border-gray-300 p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Employee name</span>
            <p className="text-sm text-gray-900">{payrollData.user_name}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">Address</span>
            <p className="text-sm text-gray-900">&nbsp;</p>
          </div>
        </div>
      </div>

      {/* Main Payroll Table */}
      <div className="grid grid-cols-4 text-sm">
        {/* Headers */}
        <div className="bg-gray-100 border-b border-r border-gray-300 p-2 font-medium text-center">
          This Pay Period Earnings
        </div>
        <div className="bg-gray-100 border-b border-r border-gray-300 p-2 font-medium text-center">
          YTD Amount
        </div>
        <div className="bg-gray-100 border-b border-r border-gray-300 p-2 font-medium text-center">
          This Pay Period Deductions
        </div>
        <div className="bg-gray-100 border-b border-gray-300 p-2 font-medium text-center">
          YTD Amount
        </div>

        {/* Sub-headers */}
        <div className="grid grid-cols-3 col-span-1 border-r border-gray-300">
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Pay</div>
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Hours</div>
          <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Rate</div>
        </div>
        <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Amount</div>
        <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Deductions</div>
        <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Amount</div>

        {/* Salary Row */}
        <div className="grid grid-cols-3 col-span-1 border-r border-gray-300">
          <div className="border-b border-r border-gray-300 p-2 text-xs">Salary</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
            {payrollData.total_hours || '0.00'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {payrollData.hourly_wage ? formatCurrency(payrollData.hourly_wage) : ''}
          </div>
        </div>
        <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
          {formatCurrency(payrollData.earnings?.salary)}
        </div>
        <div className="border-b border-r border-gray-300 p-2 text-xs">Federal Tax</div>
        <div className="border-b border-gray-300 p-2 text-xs text-right">
          {formatCurrency(payrollData.deductions?.federal_tax)}
        </div>

        {/* Other earnings rows (empty for HourlyContractor) */}
        {['Overtime Pay', 'Vacation Pay', 'Sick Leave', 'Holiday Pay', 'Bonus Pay'].map((item, index) => (
          <React.Fragment key={item}>
            <div className="grid grid-cols-3 col-span-1 border-r border-gray-300">
              <div className="border-b border-r border-gray-300 p-2 text-xs">{item}</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">0.00</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right"></div>
            </div>
            <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
              {formatCurrency(0)}
            </div>
            {index === 0 && (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">Provincial Tax</div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  {formatCurrency(payrollData.deductions?.provincial_tax)}
                </div>
              </>
            )}
            {index === 1 && (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">CPP</div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  {formatCurrency(payrollData.deductions?.cpp)}
                </div>
              </>
            )}
            {index === 2 && (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">EI</div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  {formatCurrency(payrollData.deductions?.ei)}
                </div>
              </>
            )}
            {index > 2 && (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs"></div>
                <div className="border-b border-gray-300 p-2 text-xs text-right"></div>
              </>
            )}
          </React.Fragment>
        ))}

        {/* Total Earnings Row */}
        <div className="grid grid-cols-3 col-span-1 border-r border-gray-300 bg-gray-50">
          <div className="border-b border-r border-gray-300 p-2 text-xs font-bold">Total Earnings</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs"></div>
          <div className="border-b border-gray-300 p-2 text-xs"></div>
        </div>
        <div className="border-b border-r border-gray-300 p-2 text-xs text-right font-bold bg-gray-50">
          {formatCurrency(payrollData.totals?.total_earnings)}
        </div>
        <div className="border-b border-r border-gray-300 p-2 text-xs font-bold bg-gray-50">Total Deductions</div>
        <div className="border-b border-gray-300 p-2 text-xs text-right font-bold bg-gray-50">
          {formatCurrency(payrollData.totals?.total_deductions)}
        </div>
      </div>

      {/* Bottom Summary */}
      <div className="border-t-2 border-gray-400 bg-gray-50">
        <div className="grid grid-cols-2 text-sm">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between">
              <span className="font-medium">Total Earnings This Period</span>
              <span>{formatCurrency(payrollData.totals?.total_earnings)}</span>
            </div>
          </div>
          <div className="p-2">
            <div className="flex justify-between">
              <span className="font-medium">YTD Amount</span>
              <span>{formatCurrency(payrollData.ytd_amounts?.earnings)}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 text-sm border-t border-gray-300">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between">
              <span className="font-medium">Total Deductions This Period</span>
              <span>{formatCurrency(payrollData.totals?.total_deductions)}</span>
            </div>
          </div>
          <div className="p-2">
            <div className="flex justify-between">
              <span className="font-medium">YTD Amount</span>
              <span>{formatCurrency(payrollData.ytd_amounts?.deductions)}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 text-sm border-t border-gray-300">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between">
              <span className="font-medium">Total Pay Discrepancy from previous pay</span>
              <span>{formatCurrency(0)}</span>
            </div>
          </div>
          <div className="p-2"></div>
        </div>

        <div className="grid grid-cols-2 text-sm border-t-2 border-gray-400">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between font-bold">
              <span>Net Payment This Period</span>
              <span>{formatCurrency(payrollData.totals?.net_payment)}</span>
            </div>
          </div>
          <div className="p-2"></div>
        </div>
      </div>

      {/* Notes Section */}
      <div className="border-t border-gray-300 p-4">
        <div className="text-sm font-medium text-gray-700 mb-2">Notes</div>
        <div className="min-h-[60px] border border-gray-300 p-2 text-sm bg-gray-50">
          {/* Notes will be added via props or state */}
        </div>
      </div>
    </div>
  );
}
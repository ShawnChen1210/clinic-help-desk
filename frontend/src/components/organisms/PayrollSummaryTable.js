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

  // Determine which pay types to show
  const showOvertimePay = (payrollData.breakdown?.overtime_hours > 0) || (payrollData.earnings?.overtime_pay > 0);
  const showVacationPay = payrollData.earnings?.vacation_pay > 0;

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
      <div className="grid grid-cols-2 text-sm">
        {/* Main Headers */}
        <div className="bg-gray-100 border-b border-r border-gray-300 p-2 font-medium text-center">
          This Pay Period Earnings
        </div>
        <div className="bg-gray-100 border-b border-gray-300 p-2 font-medium text-center">
          This Pay Period Deductions
        </div>

        {/* Sub-headers */}
        <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Pay Type</div>
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Hours</div>
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Rate</div>
          <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Amount</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Deductions</div>
          <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Amount</div>
        </div>

        {/* Regular Pay Row */}
        <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
          <div className="border-b border-r border-gray-300 p-2 text-xs">Regular Pay</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
            {payrollData.breakdown?.regular_hours || payrollData.total_hours || '0.00'}
          </div>
          <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
            {payrollData.hourly_wage ? formatCurrency(payrollData.hourly_wage) : ''}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {formatCurrency(payrollData.earnings?.regular_pay || payrollData.earnings?.salary)}
          </div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">Federal Tax</div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {formatCurrency(payrollData.deductions?.federal_tax)}
          </div>
        </div>

        {/* Overtime Pay Row (only show if exists) */}
        {showOvertimePay && (
          <>
            <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
              <div className="border-b border-r border-gray-300 p-2 text-xs">Overtime Pay</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                {payrollData.breakdown?.overtime_hours || '0.00'}
              </div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                {formatCurrency((payrollData.hourly_wage || 0) * 1.5)}
              </div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.earnings?.overtime_pay)}
              </div>
            </div>
            <div className="grid grid-cols-2 col-span-1">
              <div className="border-b border-r border-gray-300 p-2 text-xs">Provincial Tax</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.deductions?.provincial_tax)}
              </div>
            </div>
          </>
        )}

        {/* Vacation Pay Row (only show if exists) */}
        {showVacationPay && (
          <>
            <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
              <div className="border-b border-r border-gray-300 p-2 text-xs">Vacation Pay</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.earnings?.vacation_pay)}
              </div>
            </div>
            <div className="grid grid-cols-2 col-span-1">
              <div className="border-b border-r border-gray-300 p-2 text-xs">CPP</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.deductions?.cpp)}
              </div>
            </div>
          </>
        )}

        {/* If no overtime pay shown, show Provincial Tax in empty row */}
        {!showOvertimePay && (
          <>
            <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
            </div>
            <div className="grid grid-cols-2 col-span-1">
              <div className="border-b border-r border-gray-300 p-2 text-xs">Provincial Tax</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.deductions?.provincial_tax)}
              </div>
            </div>
          </>
        )}

        {/* If no vacation pay shown, show CPP in empty row */}
        {!showVacationPay && (
          <>
            <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
            </div>
            <div className="grid grid-cols-2 col-span-1">
              <div className="border-b border-r border-gray-300 p-2 text-xs">CPP</div>
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.deductions?.cpp)}
              </div>
            </div>
          </>
        )}

        {/* EI Row */}
        <div className="grid grid-cols-4 col-span-1 border-r border-gray-300">
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">EI</div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {formatCurrency(payrollData.deductions?.ei)}
          </div>
        </div>

        {/* Total Earnings Row */}
        <div className="grid grid-cols-4 col-span-1 border-r border-gray-300 bg-gray-50">
          <div className="border-b border-r border-gray-300 p-2 text-xs font-bold" style={{ gridColumn: '1 / 4' }}>Total Earnings</div>
          <div className="border-b border-gray-300 p-2 text-xs text-right font-bold">
            {formatCurrency(payrollData.totals?.total_earnings)}
          </div>
        </div>
        <div className="grid grid-cols-2 col-span-1 bg-gray-50">
          <div className="border-b border-r border-gray-300 p-2 text-xs font-bold">Total Deductions</div>
          <div className="border-b border-gray-300 p-2 text-xs text-right font-bold">
            {formatCurrency(payrollData.totals?.total_deductions)}
          </div>
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
              <span className="font-medium">YTD Earnings</span>
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
              <span className="font-medium">YTD Deductions</span>
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
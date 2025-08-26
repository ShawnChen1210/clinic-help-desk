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

  // Determine payroll type
  const isCommissionBased = payrollData.role_type?.includes('Commission') || false;
  const isHourlyBased = payrollData.role_type?.includes('Hourly') || false;
  const isEmployee = payrollData.role_type?.includes('Employee') || false;

  // Determine which pay types to show
  const showOvertimePay = isHourlyBased && ((payrollData.breakdown?.overtime_hours > 0) || (payrollData.earnings?.overtime_pay > 0));
  const showVacationPay = (isHourlyBased && payrollData.earnings?.vacation_pay > 0) ||
                         (isCommissionBased && isEmployee && payrollData.earnings?.vacation_pay > 0);
  const showRevenueShareIncome = payrollData.earnings?.revenue_share_income > 0;
  const showRentDeduction = payrollData.deductions?.rent > 0;
  const showRevenueShareDeduction = payrollData.deductions?.revenue_share_deduction > 0;

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
            <span className="text-sm font-medium text-gray-700">Role</span>
            <p className="text-sm text-gray-900">{payrollData.role_type}</p>
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
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">
            {isCommissionBased ? 'Income Type' : 'Pay Type'}
          </div>
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">
            {isCommissionBased ? 'Commission Rate' : 'Hours'}
          </div>
          {!isCommissionBased && (
              <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Rate</div>
          )}
          <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Amount</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="bg-gray-50 border-b border-r border-gray-300 p-2 text-xs font-medium text-center">Deductions</div>
          <div className="bg-gray-50 border-b border-gray-300 p-2 text-xs font-medium text-center">Amount</div>
        </div>

        {/* First Row - Primary Income */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {isCommissionBased ? (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">Gross Income (GST Included)</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {(payrollData.commission_rate * 100).toFixed(1)}%
                </div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  {formatCurrency(payrollData.earnings?.gross_income)}
                </div>
              </>
          ) : (
              <>
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
              </>
          )}
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased ? 'Commission Deduction' : 'Federal Tax'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {isCommissionBased ?
                formatCurrency(payrollData.deductions?.commission_deduction) :
                formatCurrency(payrollData.deductions?.federal_tax)
            }
          </div>
        </div>

        {/* Second Row */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {isCommissionBased ? (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">GST</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  {formatCurrency(payrollData.earnings?.tax_gst)}
                </div>
              </>
          ) : showOvertimePay ? (
              <>
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
              </>
          ) : (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
                {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
                <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
              </>
          )}
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased ? 'POS Fees' : 'Provincial Tax'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {isCommissionBased ?
                formatCurrency(payrollData.deductions?.pos_fees || payrollData.earnings?.pos_fees) :
                formatCurrency(payrollData.deductions?.provincial_tax)
            }
          </div>
        </div>

        {/* Third Row - Vacation Pay */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {showVacationPay ? (
            <>
              <div className="border-b border-r border-gray-300 p-2 text-xs">Vacation Pay</div>
              {isCommissionBased ? (
                <>
                  <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                  <div className="border-b border-gray-300 p-2 text-xs text-right">
                    {formatCurrency(payrollData.earnings?.vacation_pay)}
                  </div>
                </>
              ) : (
                <>
                  <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                  <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                  <div className="border-b border-gray-300 p-2 text-xs text-right">
                    {formatCurrency(payrollData.earnings?.vacation_pay)}
                  </div>
                </>
              )}
            </>
          ) : (
            <>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
              <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
            </>
          )}
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased && isEmployee ? 'Federal Tax' : 'CPP'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {isCommissionBased && isEmployee ?
              formatCurrency(payrollData.deductions?.federal_tax) :
              formatCurrency(payrollData.deductions?.cpp)
            }
          </div>
        </div>

        {/* Fourth Row - Revenue Share Income or Empty */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {showRevenueShareIncome ? (
            <>
              <div className="border-b border-r border-gray-300 p-2 text-xs">Revenue Share Income</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
              {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>}
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                {formatCurrency(payrollData.earnings?.revenue_share_income)}
              </div>
            </>
          ) : (
            <>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
              {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
              <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
            </>
          )}
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased && isEmployee ? 'Provincial Tax' : 'EI'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {isCommissionBased && isEmployee ?
              formatCurrency(payrollData.deductions?.provincial_tax) :
              formatCurrency(payrollData.deductions?.ei)
            }
          </div>
        </div>

        {/* Fifth Row - Empty for earnings, Rent deduction */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {showRentDeduction ? 'Rent' : (isCommissionBased && isEmployee ? 'CPP' : '')}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {showRentDeduction ?
              formatCurrency(payrollData.deductions?.rent) :
              (isCommissionBased && isEmployee ? formatCurrency(payrollData.deductions?.cpp) : '')
            }
          </div>
        </div>

        {/* Sixth Row - Empty for earnings, Revenue Share Deduction */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {showRevenueShareDeduction ? 'Revenue Share Deduction' : (isCommissionBased && isEmployee ? 'EI' : '')}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {showRevenueShareDeduction ?
              formatCurrency(payrollData.deductions?.revenue_share_deduction) :
              (isCommissionBased && isEmployee ? formatCurrency(payrollData.deductions?.ei) : '')
            }
          </div>
        </div>

        {/* Total Earnings Row */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300 bg-gray-50`}>
          <div className={`border-b border-r border-gray-300 p-2 text-xs font-bold ${isCommissionBased ? 'col-span-2' : 'col-span-3'}`}>
            Total Earnings
          </div>
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

      {/* Revenue Sharing Details Section */}
      {(showRevenueShareIncome || showRevenueShareDeduction || showRentDeduction) && (
        <div className="border-t border-gray-300 p-4 bg-blue-50">
          <div className="text-sm font-medium text-blue-900 mb-2">Revenue Sharing & Rent Details</div>
          <div className="text-xs text-blue-800 space-y-1">
            {showRevenueShareIncome && (
              <div>Revenue Share Income: {formatCurrency(payrollData.earnings?.revenue_share_income)}</div>
            )}
            {showRevenueShareDeduction && (
              <div>Revenue Share Deduction: {formatCurrency(payrollData.deductions?.revenue_share_deduction)}</div>
            )}
            {showRentDeduction && (
              <div>Rent Deduction: {formatCurrency(payrollData.deductions?.rent)}</div>
            )}
          </div>
        </div>
      )}

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
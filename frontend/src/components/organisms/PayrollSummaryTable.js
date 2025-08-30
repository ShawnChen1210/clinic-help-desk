import React, { useState, useEffect } from 'react';
import { useDateFormatter } from "../../hooks/useDateFormatter";

export default function PayrollSummaryTable({ payrollData, companyInfo, className = "", onDataChange }) {
  const { formatDateString } = useDateFormatter()
  const [editedData, setEditedData] = useState(payrollData);

  // Update edited data when payrollData prop changes
  useEffect(() => {
    setEditedData(payrollData);
  }, [payrollData]);

  // Notify parent of changes
  useEffect(() => {
    if (onDataChange) {
      onDataChange(editedData);
    }
  }, [editedData, onDataChange]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
      minimumFractionDigits: 2
    }).format(amount || 0);
  };

  const parseValue = (value) => {
    const cleanValue = typeof value === 'string' ? value.replace(/[$,]/g, '') : value;
    const parsed = parseFloat(cleanValue);
    return isNaN(parsed) ? 0 : parsed;
  };

  const updateNestedValue = (path, newValue) => {
    const keys = path.split('.');
    const updatedData = JSON.parse(JSON.stringify(editedData));

    // Navigate to the parent object
    let current = updatedData;
    for (let i = 0; i < keys.length - 1; i++) {
      current = current[keys[i]];
    }

    // Set the value
    current[keys[keys.length - 1]] = parseValue(newValue);

    // Recalculate totals
    const recalculatedData = recalculateTotals(updatedData);
    setEditedData(recalculatedData);
  };

  const recalculateTotals = (data) => {
    const newData = { ...data };

    // Recalculate total earnings
    if (isCommissionBased) {
      const adjustedTotal = parseValue(newData.earnings?.adjusted_total || 0);
      const taxGst = parseValue(newData.earnings?.tax_gst || 0);
      const vacationPay = parseValue(newData.earnings?.vacation_pay || 0);
      const revenueShareIncome = parseValue(newData.earnings?.revenue_share_income || 0);

      newData.earnings.gross_income = adjustedTotal + taxGst;
      newData.totals.total_earnings = adjustedTotal + taxGst + vacationPay + revenueShareIncome;
    } else {
      const regularPay = parseValue(newData.earnings?.regular_pay || newData.earnings?.salary || 0);
      const overtimePay = parseValue(newData.earnings?.overtime_pay || 0);
      const vacationPay = parseValue(newData.earnings?.vacation_pay || 0);
      const revenueShareIncome = parseValue(newData.earnings?.revenue_share_income || 0);

      newData.totals.total_earnings = regularPay + overtimePay + vacationPay + revenueShareIncome;
    }

    // Recalculate total deductions
    const deductions = newData.deductions || {};
    const totalDeductions = Object.values(deductions).reduce((sum, value) => sum + parseValue(value || 0), 0);
    newData.totals.total_deductions = totalDeductions;

    // Recalculate net payment
    newData.totals.net_payment = newData.totals.total_earnings - newData.totals.total_deductions;

    return newData;
  };

  // Helper function to get nested value
  const getNestedValue = (obj, path) => {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  };

  // Editable cell component using react-contenteditable
  const EditableCell = ({ path, className: cellClassName = "" }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editingValue, setEditingValue] = useState('');
    const value = getNestedValue(editedData, path);

    const startEditing = () => {
      setIsEditing(true);
      setEditingValue(parseValue(value).toString());
    };

    const saveEditing = () => {
      if (isEditing) {
        updateNestedValue(path, editingValue);
        setIsEditing(false);
        setEditingValue('');
      }
    };

    const cancelEditing = () => {
      setIsEditing(false);
      setEditingValue('');
    };

    if (isEditing) {
      return (
        <input
          type="text"
          value={editingValue}
          onChange={(e) => setEditingValue(e.target.value)}
          onBlur={saveEditing}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              saveEditing();
            } else if (e.key === 'Escape') {
              e.preventDefault();
              cancelEditing();
            }
          }}
          className={`${cellClassName} bg-yellow-100 border border-blue-300 p-1 rounded w-full`}
          style={{ textAlign: 'right' }}
          autoFocus
        />
      );
    }

    return (
      <div
        className={`${cellClassName} cursor-pointer hover:bg-gray-100 p-1 rounded`}
        onClick={startEditing}
        style={{ textAlign: 'right' }}
        title="Click to edit"
      >
        {formatCurrency(parseValue(value))}
      </div>
    );
  };

  // Determine payroll type
  const isCommissionBased = editedData.role_type?.includes('Commission') || false;
  const isHourlyBased = editedData.role_type?.includes('Hourly') || false;
  const isEmployee = editedData.role_type?.includes('Employee') || false;

  // Determine which pay types to show
  const showOvertimePay = isHourlyBased && ((editedData.breakdown?.overtime_hours > 0) || (editedData.earnings?.overtime_pay > 0));
  const showVacationPay = (isHourlyBased && editedData.earnings?.vacation_pay > 0) ||
                         (isCommissionBased && isEmployee && editedData.earnings?.vacation_pay > 0);
  const showRevenueShareIncome = editedData.earnings?.revenue_share_income > 0;
  const showRentDeduction = editedData.deductions?.rent > 0;
  const showRevenueShareDeduction = editedData.deductions?.revenue_share_deduction > 0;

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
          <span className="text-sm">{formatDateString(editedData.pay_period_end)}</span>
        </div>
      </div>

      {/* Employee Info */}
      <div className="border-b border-gray-300 p-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <span className="text-sm font-medium text-gray-700">Employee name</span>
            <p className="text-sm text-gray-900">{editedData.user_name}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-gray-700">Role</span>
            <p className="text-sm text-gray-900">{editedData.role_type}</p>
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
                <div className="border-b border-r border-gray-300 p-2 text-xs">Adjusted Total (Pre-GST)</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {(editedData.commission_rate * 100).toFixed(1)}%
                </div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  <EditableCell path="earnings.adjusted_total" />
                </div>
              </>
          ) : (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">Regular Pay</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {editedData.breakdown?.regular_hours || editedData.total_hours || '0.00'}
                </div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {editedData.hourly_wage ? formatCurrency(editedData.hourly_wage) : ''}
                </div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  <EditableCell path={editedData.earnings?.regular_pay ? "earnings.regular_pay" : "earnings.salary"} />
                </div>
              </>
          )}
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased ? 'Commission Deduction' : 'Federal Tax'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            <EditableCell path={isCommissionBased ? "deductions.commission_deduction" : "deductions.federal_tax"} />
          </div>
        </div>

        {/* Second Row */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {isCommissionBased ? (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">GST</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  <EditableCell path="earnings.tax_gst" />
                </div>
              </>
          ) : showOvertimePay ? (
              <>
                <div className="border-b border-r border-gray-300 p-2 text-xs">Overtime Pay</div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {editedData.breakdown?.overtime_hours || '0.00'}
                </div>
                <div className="border-b border-r border-gray-300 p-2 text-xs text-right">
                  {formatCurrency((editedData.hourly_wage || 0) * 1.5)}
                </div>
                <div className="border-b border-gray-300 p-2 text-xs text-right">
                  <EditableCell path="earnings.overtime_pay" />
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
            {isCommissionBased ? 'GST Deduction' : 'Provincial Tax'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            <EditableCell path={isCommissionBased ? "deductions.gst_deduction" : "deductions.provincial_tax"} />
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
                    <EditableCell path="earnings.vacation_pay" />
                  </div>
                </>
              ) : (
                <>
                  <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                  <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
                  <div className="border-b border-gray-300 p-2 text-xs text-right">
                    <EditableCell path="earnings.vacation_pay" />
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
            {isCommissionBased ? 'POS Fees' : 'CPP'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            <EditableCell path={isCommissionBased ? "deductions.pos_fees" : "deductions.cpp"} />
          </div>
        </div>

        {/* Continue with remaining rows using same pattern... */}
        {/* Fourth Row - Revenue Share Income */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          {showRevenueShareIncome ? (
            <>
              <div className="border-b border-r border-gray-300 p-2 text-xs">Revenue Share Income</div>
              <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>
              {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs text-right">-</div>}
              <div className="border-b border-gray-300 p-2 text-xs text-right">
                <EditableCell path="earnings.revenue_share_income" />
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
            {isCommissionBased && isEmployee ? 'Federal Tax' : 'EI'}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            <EditableCell path={isCommissionBased && isEmployee ? "deductions.federal_tax" : "deductions.ei"} />
          </div>
        </div>

        {/* Fifth Row - Rent/Provincial Tax */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {showRentDeduction ? 'Rent' : (isCommissionBased && isEmployee ? 'Provincial Tax' : '')}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {showRentDeduction ? (
              <EditableCell path="deductions.rent" />
            ) : (isCommissionBased && isEmployee ? (
              <EditableCell path="deductions.provincial_tax" />
            ) : '')}
          </div>
        </div>

        {/* Sixth Row - Revenue Share Deduction/CPP */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {showRevenueShareDeduction ? 'Revenue Share Deduction' : (isCommissionBased && isEmployee ? 'CPP' : '')}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {showRevenueShareDeduction ? (
              <EditableCell path="deductions.revenue_share_deduction" />
            ) : (isCommissionBased && isEmployee ? (
              <EditableCell path="deductions.cpp" />
            ) : '')}
          </div>
        </div>

        {/* Seventh Row - EI for commission employees */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300`}>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>
          {!isCommissionBased && <div className="border-b border-r border-gray-300 p-2 text-xs">&nbsp;</div>}
          <div className="border-b border-gray-300 p-2 text-xs">&nbsp;</div>
        </div>
        <div className="grid grid-cols-2 col-span-1">
          <div className="border-b border-r border-gray-300 p-2 text-xs">
            {isCommissionBased && isEmployee ? 'EI' : ''}
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right">
            {isCommissionBased && isEmployee ? (
              <EditableCell path="deductions.ei" />
            ) : ''}
          </div>
        </div>

        {/* Total Earnings Row */}
        <div className={`grid ${isCommissionBased ? 'grid-cols-3' : 'grid-cols-4'} col-span-1 border-r border-gray-300 bg-gray-50`}>
          <div className={`border-b border-r border-gray-300 p-2 text-xs font-bold ${isCommissionBased ? 'col-span-2' : 'col-span-3'}`}>
            Total Earnings
          </div>
          <div className="border-b border-gray-300 p-2 text-xs text-right font-bold">
            {formatCurrency(editedData.totals?.total_earnings)}
          </div>
        </div>
        <div className="grid grid-cols-2 col-span-1 bg-gray-50">
          <div className="border-b border-r border-gray-300 p-2 text-xs font-bold">Total Deductions</div>
          <div className="border-b border-gray-300 p-2 text-xs text-right font-bold">
            {formatCurrency(editedData.totals?.total_deductions)}
          </div>
        </div>
      </div>

      {/* Bottom Summary - same as before... */}
      <div className="border-t-2 border-gray-400 bg-gray-50">
        <div className="grid grid-cols-2 text-sm">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between">
              <span className="font-medium">Total Earnings This Period</span>
              <span>{formatCurrency(editedData.totals?.total_earnings)}</span>
            </div>
          </div>
          <div className="p-2">
            <div className="flex justify-between">
              <span className="font-medium">YTD Earnings</span>
              <span>{formatCurrency(editedData.ytd_amounts?.earnings)}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 text-sm border-t border-gray-300">
          <div className="p-2 border-r border-gray-300">
            <div className="flex justify-between">
              <span className="font-medium">Total Deductions This Period</span>
              <span>{formatCurrency(editedData.totals?.total_deductions)}</span>
            </div>
          </div>
          <div className="p-2">
            <div className="flex justify-between">
              <span className="font-medium">YTD Deductions</span>
              <span>{formatCurrency(editedData.ytd_amounts?.deductions)}</span>
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
              <span>{formatCurrency(editedData.totals?.net_payment)}</span>
            </div>
          </div>
          <div className="p-2"></div>
        </div>
      </div>

      {/* Revenue Sharing Details Section - same as before... */}
      {/* ... rest of component unchanged ... */}

      {/* Edit Instructions */}
      <div className="border-t border-gray-300 p-2 bg-blue-50">
        <div className="text-xs text-blue-700">
          Click any amount to edit. Press Enter or click elsewhere to save, Escape to cancel.
        </div>
      </div>
    </div>
  );
}
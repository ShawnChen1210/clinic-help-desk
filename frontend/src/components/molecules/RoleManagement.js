import React, { useState, useEffect } from 'react';
import Select from '../atoms/Select';
import Toggle from '../atoms/Toggle';

const PRIMARY_ROLES = [
  { value: '', label: 'No Primary Role' },
  { value: 'hourlyemployee', label: 'Hourly Employee' },
  { value: 'hourlycontractor', label: 'Hourly Contractor' },
  { value: 'commissionemployee', label: 'Commission Employee' },
  { value: 'commissioncontractor', label: 'Commission Contractor' },
  { value: 'student', label: 'Student' },
];

const ADDITIONAL_ROLES = [
  { value: 'profitsharing', label: 'Profit Sharing' },
  { value: 'revenuesharing', label: 'Revenue Sharing' },
  { value: 'hasrent', label: 'Has Rent' },
];

const PAYMENT_FREQUENCIES = [
  { value: 'weekly', label: 'Weekly' },
  { value: 'bi-weekly', label: 'Bi-weekly' },
  { value: 'semi-monthly', label: 'Semi-monthly' },
  { value: 'monthly', label: 'Monthly' },
];

const REVENUE_TARGET_TYPES = [
  { value: 'specific_user', label: 'Specific User' },
  { value: 'all_students', label: 'All Students' },
];

export default function RoleManagement({ user, onSave, onCancel, isLoading, isOpen }) {
  const [primaryRole, setPrimaryRole] = useState(user.primaryRole || '');
  const [additionalRoles, setAdditionalRoles] = useState(user.additionalRoles || []);
  const [isVerified, setIsVerified] = useState(user.is_verified || false);
  const [isStaff, setIsStaff] = useState(user.is_staff || false);
  const [paymentFrequency, setPaymentFrequency] = useState(user.payment_frequency || 'semi-monthly');

  // Primary role values
  const [primaryRoleValues, setPrimaryRoleValues] = useState({
    hourly_wage: user.primaryRoleData?.hourly_wage || '',
    commission_rate: user.primaryRoleData?.commission_rate || '',
  });

  // Additional role values
  const [additionalRoleValues, setAdditionalRoleValues] = useState({
    profitsharing: {
      sharing_rate: user.additionalRoleData?.profitsharing?.sharing_rate || '',
      description: user.additionalRoleData?.profitsharing?.description || ''
    },
    revenuesharing: {
      sharing_rate: user.additionalRoleData?.revenuesharing?.sharing_rate || '',
      description: user.additionalRoleData?.revenuesharing?.description || '',
      target_type: user.additionalRoleData?.revenuesharing?.target_type || 'specific_user',
      target_user: user.additionalRoleData?.revenuesharing?.target_user || ''
    },
    hasrent: {
      monthly_rent: user.additionalRoleData?.hasrent?.monthly_rent || '',
      description: user.additionalRoleData?.hasrent?.description || ''
    }
  });

  // Update state when user prop changes
  useEffect(() => {
    setPrimaryRole(user.primaryRole || '');
    setAdditionalRoles(user.additionalRoles || []);
    setIsVerified(user.is_verified || false);
    setIsStaff(user.is_staff || false);
    setPaymentFrequency(user.payment_frequency || 'semi-monthly');

    setPrimaryRoleValues({
      hourly_wage: user.primaryRoleData?.hourly_wage || '',
      commission_rate: user.primaryRoleData?.commission_rate || '',
    });

    setAdditionalRoleValues({
      profitsharing: {
        sharing_rate: user.additionalRoleData?.profitsharing?.sharing_rate || '',
        description: user.additionalRoleData?.profitsharing?.description || ''
      },
      revenuesharing: {
        sharing_rate: user.additionalRoleData?.revenuesharing?.sharing_rate || '',
        description: user.additionalRoleData?.revenuesharing?.description || '',
        target_type: user.additionalRoleData?.revenuesharing?.target_type || 'specific_user',
        target_user: user.additionalRoleData?.revenuesharing?.target_user || ''
      },
      hasrent: {
        monthly_rent: user.additionalRoleData?.hasrent?.monthly_rent || '',
        description: user.additionalRoleData?.hasrent?.description || ''
      }
    });
  }, [user]);

  const handleAdditionalRoleToggle = (roleValue) => {
    setAdditionalRoles(prev =>
      prev.includes(roleValue)
        ? prev.filter(role => role !== roleValue)
        : [...prev, roleValue]
    );
  };

  const handlePrimaryRoleValueChange = (field, value) => {
    // Handle empty string case
    if (value === '') {
      setPrimaryRoleValues(prev => ({
        ...prev,
        [field]: ''
      }));
      return;
    }

    // Handle percentage fields (commission_rate)
    if (field === 'commission_rate') {
      if (value < 0) value = 0;
      if (value > 1) value = 1;
    }
    // Handle wage fields (allow negative to be reset to 0)
    else if (field === 'hourly_wage') {
      if (value < 0) value = 0;
    }

    setPrimaryRoleValues(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleAdditionalRoleValueChange = (roleType, field, value) => {
    // Handle empty string case
    if (value === '') {
      setAdditionalRoleValues(prev => ({
        ...prev,
        [roleType]: {
          ...prev[roleType],
          [field]: ''
        }
      }));
      return;
    }

    // Handle percentage fields
    if (field === 'sharing_rate') {
      if (value < 0) value = 0;
      if (value > 1) value = 1;
    }
    // Handle monetary fields
    else if (field === 'monthly_rent') {
      if (value < 0) value = 0;
    }

    setAdditionalRoleValues(prev => ({
      ...prev,
      [roleType]: {
        ...prev[roleType],
        [field]: value
      }
    }));

    // Clear target_user when switching to 'all_students'
    if (roleType === 'revenuesharing' && field === 'target_type' && value === 'all_students') {
      setAdditionalRoleValues(prev => ({
        ...prev,
        revenuesharing: {
          ...prev.revenuesharing,
          target_user: ''
        }
      }));
    }
  };

  const handleSave = () => {
    // Convert empty strings to 0 for API call, but handle different field types
    const processedPrimaryRoleValues = {};
    Object.keys(primaryRoleValues).forEach(key => {
      processedPrimaryRoleValues[key] = primaryRoleValues[key] === '' ? 0 : primaryRoleValues[key];
    });

    // Only include data for roles that are actually selected
    const processedAdditionalRoleValues = {};
    additionalRoles.forEach(roleType => {
      if (additionalRoleValues[roleType]) {
        processedAdditionalRoleValues[roleType] = {};
        Object.keys(additionalRoleValues[roleType]).forEach(field => {
          const value = additionalRoleValues[roleType][field];

          // Handle different field types appropriately
          if (field === 'description') {
            // Description should remain a string, empty string if empty
            processedAdditionalRoleValues[roleType][field] = value === '' ? '' : value;
          } else if (field === 'target_user') {
            // Target user should be null if empty, not 0
            processedAdditionalRoleValues[roleType][field] = value === '' || value === 0 ? null : value;
          } else if (field === 'target_type') {
            // Target type should remain as string
            processedAdditionalRoleValues[roleType][field] = value;
          } else {
            // Numeric fields (rates, rent) should be 0 if empty
            processedAdditionalRoleValues[roleType][field] = value === '' ? 0 : value;
          }
        });
      }
    });

    onSave({
      userId: user.id,
      primary_role: primaryRole,
      additional_roles: additionalRoles,
      is_verified: isVerified,
      is_staff: isStaff,
      payment_frequency: paymentFrequency,
      primaryRoleValues: processedPrimaryRoleValues,
      additionalRoleValues: processedAdditionalRoleValues
    });
  };

  const renderPrimaryRoleInputs = () => {
    if (!primaryRole) return null;

    if (primaryRole === 'hourlyemployee' || primaryRole === 'hourlycontractor') {
      return (
        <div className="mt-2">
          <label className="block text-sm font-medium text-gray-600 mb-1">Hourly Wage ($)</label>
          <input
            type="number"
            step="0.01"
            min="0"
            value={primaryRoleValues.hourly_wage}
            onChange={(e) => handlePrimaryRoleValueChange('hourly_wage', e.target.value === '' ? '' : parseFloat(e.target.value) || 0)}
            disabled={isLoading}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
        </div>
      );
    }

    if (primaryRole === 'commissionemployee' || primaryRole === 'commissioncontractor') {
      return (
        <div className="mt-2">
          <label className="block text-sm font-medium text-gray-600 mb-1">Commission Rate (decimal, e.g., 0.15 for 15%)</label>
          <input
            type="number"
            step="0.01"
            min="0"
            max="1"
            value={primaryRoleValues.commission_rate}
            onChange={(e) => handlePrimaryRoleValueChange('commission_rate', e.target.value === '' ? '' : parseFloat(e.target.value) || 0)}
            disabled={isLoading}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
          />
        </div>
      );
    }

    if (primaryRole === 'student') {
      return (
        <div className="mt-2 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <p className="text-sm text-blue-700">
            Student role requires no additional configuration. Students are not eligible for payroll generation.
          </p>
        </div>
      );
    }

    return null;
  };

  const renderAdditionalRoleInputs = (roleType) => {
    if (!additionalRoles.includes(roleType)) return null;

    const roleData = additionalRoleValues[roleType];

    switch (roleType) {
      case 'profitsharing':
        return (
          <div key={roleType} className="mt-2 p-3 bg-white border border-gray-200 rounded-md">
            <h5 className="font-medium text-gray-800 mb-2">Profit Sharing Details</h5>
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Description</label>
                <input
                  type="text"
                  value={roleData.description}
                  onChange={(e) => handleAdditionalRoleValueChange('profitsharing', 'description', e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Sharing Rate (decimal, e.g., 0.10 for 10%)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={roleData.sharing_rate}
                  onChange={(e) => handleAdditionalRoleValueChange('profitsharing', 'sharing_rate', e.target.value === '' ? '' : parseFloat(e.target.value) || 0)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        );

      case 'revenuesharing':
        return (
          <div key={roleType} className="mt-2 p-3 bg-white border border-gray-200 rounded-md">
            <h5 className="font-medium text-gray-800 mb-2">Revenue Sharing Details</h5>
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Description</label>
                <input
                  type="text"
                  value={roleData.description}
                  onChange={(e) => handleAdditionalRoleValueChange('revenuesharing', 'description', e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Target</label>
                <Select
                  options={REVENUE_TARGET_TYPES}
                  value={roleData.target_type}
                  onChange={(e) => handleAdditionalRoleValueChange('revenuesharing', 'target_type', e.target.value)}
                  disabled={isLoading}
                />
              </div>
              {roleData.target_type === 'specific_user' && (
                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-1">Target User (Username)</label>
                  <input
                    type="text"
                    value={roleData.target_user}
                    onChange={(e) => handleAdditionalRoleValueChange('revenuesharing', 'target_user', e.target.value)}
                    disabled={isLoading}
                    placeholder="Enter username"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                  />
                </div>
              )}
              {roleData.target_type === 'all_students' && (
                <div className="p-2 bg-blue-50 border border-blue-200 rounded-md">
                  <p className="text-sm text-blue-700">
                    This revenue sharing will apply to all users with the Student role.
                  </p>
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Sharing Rate (decimal, e.g., 0.10 for 10%)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max="1"
                  value={roleData.sharing_rate}
                  onChange={(e) => handleAdditionalRoleValueChange('revenuesharing', 'sharing_rate', e.target.value === '' ? '' : parseFloat(e.target.value) || 0)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        );

      case 'hasrent':
        return (
          <div key={roleType} className="mt-2 p-3 bg-white border border-gray-200 rounded-md">
            <h5 className="font-medium text-gray-800 mb-2">Rent Details</h5>
            <div className="space-y-2">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Description</label>
                <input
                  type="text"
                  value={roleData.description}
                  onChange={(e) => handleAdditionalRoleValueChange('hasrent', 'description', e.target.value)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1">Monthly Rent ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={roleData.monthly_rent}
                  onChange={(e) => handleAdditionalRoleValueChange('hasrent', 'monthly_rent', e.target.value === '' ? '' : parseFloat(e.target.value) || 0)}
                  disabled={isLoading}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
                />
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
      <div
          className="fixed -inset-5 -top-10 -left-4 -right-4 -bottom-4 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-lg z-10">
            <div className="flex items-center justify-between">
              <h4 className="text-lg font-semibold text-gray-900">Manage Roles for {user.username}</h4>
              <button
                  onClick={onCancel}
                  disabled={isLoading}
                  className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <div className="px-6 py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Primary Role</label>
              <Select
                  options={PRIMARY_ROLES}
                  value={primaryRole}
                  onChange={(e) => setPrimaryRole(e.target.value)}
                  disabled={isLoading}
              />
              {renderPrimaryRoleInputs()}
            </div>

            {/* Payment Frequency Section - only show if user has a payroll-eligible primary role */}
            {primaryRole && primaryRole !== 'student' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Payment Frequency</label>
                <Select
                    options={PAYMENT_FREQUENCIES}
                    value={paymentFrequency}
                    onChange={(e) => setPaymentFrequency(e.target.value)}
                    disabled={isLoading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Determines how often payroll can be generated for this user
                </p>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Additional Roles</label>
              <div className="space-y-2">
                {ADDITIONAL_ROLES.map((role) => (
                    <div key={role.value}>
                      <Toggle
                          checked={additionalRoles.includes(role.value)}
                          onChange={() => handleAdditionalRoleToggle(role.value)}
                          label={role.label}
                          disabled={isLoading}
                      />
                      {renderAdditionalRoleInputs(role.value)}
                    </div>
                ))}
              </div>
            </div>

            <div>
              <Toggle
                  checked={isVerified}
                  onChange={(e) => setIsVerified(e.target.checked)}
                  label="User is verified (can access dashboard)"
                  disabled={isLoading}
              />
            </div>

            <div>
              <Toggle
                  checked={isStaff}
                  onChange={(e) => setIsStaff(e.target.checked)}
                  label="Staff privileges (can manage other users and access admin features)"
                  disabled={isLoading}
              />
              <p className="text-xs text-red-500 mt-1">
                ⚠️ Staff users can manage roles, generate payroll, and access sensitive features
              </p>
            </div>
          </div>

          <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 rounded-b-lg z-10">
            <div className="flex gap-3 justify-end">
              <button
                  onClick={onCancel}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition duration-200"
              >
                Cancel
              </button>
              <button
                  onClick={handleSave}
                  disabled={isLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition duration-200"
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      </div>
  );
}
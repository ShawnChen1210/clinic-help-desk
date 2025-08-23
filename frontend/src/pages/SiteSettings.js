import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../utils/axiosConfig';

const SiteSettings = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    id: null,
    federal_tax_brackets: [],
    provincial_tax_brackets: [],
    cpp: '',
    cpp_exemption: '',
    cpp_cap: '',
    ei_ee: '',
    ei_er: '',
    ei_cap: '',
    vacation_pay_rate: '',
    overtime_pay_rate: ''
  });
  const [error, setError] = useState('');
  const [currentUser, setCurrentUser] = useState(null);

  // Check auth and load settings
  useEffect(() => {
    fetchUserAndSettings();
  }, []);

  const fetchUserAndSettings = async () => {
    try {
      // Check user permissions
      const userResponse = await api.get('/api/members/current-user/');
      setCurrentUser(userResponse.data);

      if (!userResponse.data.is_staff && !userResponse.data.is_superuser) {
        setError('Access denied. Staff privileges required.');
        return;
      }

      // Fetch settings
      const settingsResponse = await api.get('/api/site-settings/');
      if (settingsResponse.data.length > 0) {
        const settingsData = settingsResponse.data[0];
        setSettings({
          ...settingsData,
          federal_tax_brackets: settingsData.federal_tax_brackets || [],
          provincial_tax_brackets: settingsData.provincial_tax_brackets || [],
          cpp: settingsData.cpp || '',
          cpp_exemption: settingsData.cpp_exemption || '',
          cpp_cap: settingsData.cpp_cap || '',
          ei_ee: settingsData.ei_ee || '',
          ei_er: settingsData.ei_er || '',
          ei_cap: settingsData.ei_cap || '',
          vacation_pay_rate: settingsData.vacation_pay_rate || '',
          overtime_pay_rate: settingsData.overtime_pay_rate || ''
        });
      }
    } catch (err) {
      console.error('Error fetching user/settings:', err);
      setError('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  // Simplified bracket management with tax bracket validation
  const addBracket = (type) => {
    setSettings(prev => {
      const currentBrackets = prev[type] || [];
      const lastBracket = currentBrackets[currentBrackets.length - 1];

      // Set min_income to the previous bracket's max_income (or 0 for first bracket)
      const newMinIncome = lastBracket ? lastBracket.max_income : '0';

      return {
        ...prev,
        [type]: [...currentBrackets, {
          tax_rate: '',
          min_income: newMinIncome,
          max_income: ''
        }]
      };
    });
  };

  const updateBracket = (type, index, field, value) => {
    setSettings(prev => {
      const currentBrackets = prev[type] || [];

      return {
        ...prev,
        [type]: currentBrackets.map((bracket, i) => {
          if (i === index) {
            let updatedBracket = { ...bracket, [field]: value };

            // If updating max_income, update the next bracket's min_income
            if (field === 'max_income' && i < currentBrackets.length - 1) {
              // This will be handled by the next render, but we could update it here too
            }

            return updatedBracket;
          }

          // If the previous bracket's max_income changed, update this bracket's min_income
          if (i === index + 1 && field === 'max_income') {
            return { ...bracket, min_income: value };
          }

          return bracket;
        })
      };
    });
  };

  const removeBracket = (type, index) => {
    setSettings(prev => {
      const currentBrackets = prev[type] || [];
      const newBrackets = currentBrackets.filter((_, i) => i !== index);

      // If we removed a middle bracket, update the next bracket's min_income
      if (index > 0 && index < currentBrackets.length - 1) {
        const prevBracket = newBrackets[index - 1];
        if (newBrackets[index]) {
          newBrackets[index] = {
            ...newBrackets[index],
            min_income: prevBracket.max_income
          };
        }
      }

      return {
        ...prev,
        [type]: newBrackets
      };
    });
  };

  // Get minimum allowed value for min_income based on previous bracket
  const getMinIncomeMinValue = (brackets, currentIndex) => {
    if (currentIndex === 0) return '0';
    const prevBracket = brackets[currentIndex - 1];
    return prevBracket ? prevBracket.max_income : '0';
  };

  // Enhanced form validation
  const validateAndSave = async (e) => {
    e.preventDefault();
    setError('');

    // Basic validation
    const { cpp, cpp_exemption, cpp_cap, ei_ee, ei_er, ei_cap, vacation_pay_rate, overtime_pay_rate } = settings;
    if (!cpp || !cpp_exemption || !cpp_cap || !ei_ee || !ei_er || !ei_cap || !vacation_pay_rate || !overtime_pay_rate) {
      setError('All tax rate and pay rate fields are required');
      return;
    }

    // Validate CPP exemption vs cap
    if (parseFloat(cpp_cap) <= parseFloat(cpp_exemption)) {
      setError('CPP maximum pensionable earnings must be greater than the basic exemption');
      return;
    }

    // Validate tax bracket sequences
    const validateBracketSequence = (brackets, type) => {
      for (let i = 0; i < brackets.length; i++) {
        const bracket = brackets[i];

        // Check required fields
        if (!bracket.tax_rate || !bracket.min_income || !bracket.max_income) {
          return `${type} bracket ${i + 1}: All fields are required`;
        }

        // Check max > min
        if (parseFloat(bracket.max_income) <= parseFloat(bracket.min_income)) {
          return `${type} bracket ${i + 1}: Maximum income must be greater than minimum income`;
        }

        // Check sequence (except for first bracket)
        if (i > 0) {
          const prevBracket = brackets[i - 1];
          if (parseFloat(bracket.min_income) < parseFloat(prevBracket.max_income)) {
            return `${type} bracket ${i + 1}: Minimum income must be at least ${prevBracket.max_income}`;
          }
        }
      }
      return null;
    };

    // Validate federal brackets
    if (settings.federal_tax_brackets && settings.federal_tax_brackets.length > 0) {
      const federalError = validateBracketSequence(settings.federal_tax_brackets, 'Federal');
      if (federalError) {
        setError(federalError);
        return;
      }
    }

    // Validate provincial brackets
    if (settings.provincial_tax_brackets && settings.provincial_tax_brackets.length > 0) {
      const provincialError = validateBracketSequence(settings.provincial_tax_brackets, 'Provincial');
      if (provincialError) {
        setError(provincialError);
        return;
      }
    }

    setSaving(true);
    try {
      let response;
      if (settings.id) {
        response = await api.put(`/api/site-settings/${settings.id}/`, settings);
      } else {
        response = await api.post('/api/site-settings/', settings);
      }

      setSettings(response.data);
      alert('Settings saved successfully!');
    } catch (err) {
      console.error('Save error:', err);
      if (err.response?.data) {
        setError(Object.values(err.response.data).flat().join(', '));
      } else {
        setError('Failed to save settings');
      }
    } finally {
      setSaving(false);
    }
  };

  // Render bracket card with validation
  const renderBracket = (bracket, index, type, title) => {
    const brackets = settings[type] || [];
    const minAllowed = getMinIncomeMinValue(brackets, index);
    const isFirstBracket = index === 0;

    return (
      <div key={index} className="border p-4 rounded bg-gray-50">
        <div className="flex justify-between items-center mb-3">
          <h3 className="font-medium">{title} {index + 1}</h3>
          <button
            type="button"
            onClick={() => removeBracket(type, index)}
            className="text-red-500 hover:text-red-700"
          >
            Remove
          </button>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium mb-1">Tax Rate (%)</label>
            <input
              type="number"
              step="0.01"
              placeholder="15.00"
              value={bracket.tax_rate}
              onChange={(e) => updateBracket(type, index, 'tax_rate', e.target.value)}
              className="border rounded px-3 py-2 w-full"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Min Income ($)
              {!isFirstBracket && (
                <span className="text-xs text-gray-500 ml-1">
                  (≥ {minAllowed})
                </span>
              )}
            </label>
            <input
              type="number"
              step="0.01"
              placeholder="0"
              value={bracket.min_income}
              min={minAllowed}
              onChange={(e) => {
                const value = e.target.value;
                // Only allow values >= minimum allowed
                if (!value || parseFloat(value) >= parseFloat(minAllowed)) {
                  updateBracket(type, index, 'min_income', value);
                }
              }}
              className={`border rounded px-3 py-2 w-full ${
                !isFirstBracket ? 'bg-gray-100' : ''
              }`}
              title={!isFirstBracket ? `Minimum value: ${minAllowed}` : ''}
            />
            {!isFirstBracket && (
              <p className="text-xs text-gray-500 mt-1">
                Auto-set from previous bracket's maximum
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Max Income ($)</label>
            <input
              type="number"
              step="0.01"
              placeholder="50000"
              value={bracket.max_income}
              min={bracket.min_income || '0'}
              onChange={(e) => {
                const value = e.target.value;
                updateBracket(type, index, 'max_income', value);

                // Auto-update next bracket's min_income
                const nextIndex = index + 1;
                if (brackets[nextIndex] && value) {
                  updateBracket(type, nextIndex, 'min_income', value);
                }
              }}
              className="border rounded px-3 py-2 w-full"
            />
          </div>
        </div>

        {/* Validation warnings */}
        {bracket.min_income && bracket.max_income &&
         parseFloat(bracket.max_income) <= parseFloat(bracket.min_income) && (
          <div className="mt-2 text-sm text-red-600">
            ⚠️ Maximum income must be greater than minimum income
          </div>
        )}
      </div>
    );
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Permission check
  if (!currentUser || (!currentUser.is_staff && !currentUser.is_superuser)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
          <p className="text-gray-600">You don't have permission to access site settings.</p>
          <button
            onClick={() => navigate('/chd-app/clinics')}
            className="mt-4 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            Back to Clinics
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900">Site Settings</h1>
            <button
              onClick={() => navigate('/chd-app/clinics')}
              className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
            >
              Back to Clinics
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="px-6 py-4 bg-red-50 border-b border-gray-200">
              <p className="text-red-700">{error}</p>
              <button onClick={() => setError('')} className="text-red-500 underline">
                Dismiss
              </button>
            </div>
          )}

          {/* Settings Form */}
          <form onSubmit={validateAndSave} className="p-6 space-y-8">
            {/* Federal Tax Brackets */}
            <div className="border rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl font-semibold">Federal Tax Brackets</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    Tax brackets are applied in order. Each bracket's minimum is automatically set to the previous bracket's maximum.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => addBracket('federal_tax_brackets')}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  + Add
                </button>
              </div>
              <div className="space-y-4">
                {(settings.federal_tax_brackets || []).map((bracket, index) =>
                  renderBracket(bracket, index, 'federal_tax_brackets', 'Federal Bracket')
                )}
                {(!settings.federal_tax_brackets || settings.federal_tax_brackets.length === 0) && (
                  <p className="text-gray-500 text-center py-4">No federal tax brackets added yet.</p>
                )}
              </div>
            </div>

            {/* Provincial Tax Brackets */}
            <div className="border rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Provincial Tax Brackets</h2>
                <button
                  type="button"
                  onClick={() => addBracket('provincial_tax_brackets')}
                  className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
                >
                  + Add
                </button>
              </div>
              <div className="space-y-4">
                {(settings.provincial_tax_brackets || []).map((bracket, index) =>
                  renderBracket(bracket, index, 'provincial_tax_brackets', 'Provincial Bracket')
                )}
                {(!settings.provincial_tax_brackets || settings.provincial_tax_brackets.length === 0) && (
                  <p className="text-gray-500 text-center py-4">No provincial tax brackets added yet.</p>
                )}
              </div>
            </div>

            {/* Tax Rate Settings */}
            <div className="border rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Tax Rates & Limits</h2>

              {/* CPP Settings */}
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-3 text-gray-800">Canada Pension Plan (CPP)</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">CPP Rate (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      required
                      value={settings.cpp}
                      onChange={(e) => setSettings(prev => ({ ...prev, cpp: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="5.95"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">CPP Basic Exemption ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={settings.cpp_exemption}
                      onChange={(e) => setSettings(prev => ({ ...prev, cpp_exemption: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="3500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Income below this amount is exempt from CPP</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">CPP Maximum Pensionable Earnings ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={settings.cpp_cap}
                      onChange={(e) => setSettings(prev => ({ ...prev, cpp_cap: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="68500"
                    />
                    <p className="text-xs text-gray-500 mt-1">Maximum annual income subject to CPP</p>
                  </div>
                </div>
              </div>

              {/* EI Settings */}
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-3 text-gray-800">Employment Insurance (EI)</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">EI Employee Rate (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      required
                      value={settings.ei_ee}
                      onChange={(e) => setSettings(prev => ({ ...prev, ei_ee: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="1.62"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">EI Employer Rate (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      required
                      value={settings.ei_er}
                      onChange={(e) => setSettings(prev => ({ ...prev, ei_er: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="2.27"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">EI Maximum Insurable Earnings ($)</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={settings.ei_cap}
                      onChange={(e) => setSettings(prev => ({ ...prev, ei_cap: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="63700"
                    />
                    <p className="text-xs text-gray-500 mt-1">Maximum annual income subject to EI</p>
                  </div>
                </div>
              </div>

              {/* Pay Rate Settings */}
              <div>
                <h3 className="text-lg font-medium mb-3 text-gray-800">Pay Rates</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Vacation Pay Rate (%)</label>
                    <input
                      type="number"
                      step="0.001"
                      required
                      value={settings.vacation_pay_rate}
                      onChange={(e) => setSettings(prev => ({ ...prev, vacation_pay_rate: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="4.0"
                    />
                    <p className="text-xs text-gray-500 mt-1">Percentage of gross pay for vacation pay</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Overtime Pay Rate Multiplier</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={settings.overtime_pay_rate}
                      onChange={(e) => setSettings(prev => ({ ...prev, overtime_pay_rate: e.target.value }))}
                      className="w-full border rounded px-3 py-2"
                      placeholder="1.5"
                    />
                    <p className="text-xs text-gray-500 mt-1">Multiplier for overtime hours (e.g., 1.5 = time and a half)</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={saving}
                className="bg-green-500 text-white px-6 py-3 rounded hover:bg-green-600 disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SiteSettings;
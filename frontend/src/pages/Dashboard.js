import React from 'react';
import { useClinic } from '../context/ClinicContext';
import IncomeReport from "../components/organisms/IncomeReport";

function Dashboard() {
  const { clinicName } = useClinic();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white shadow rounded-lg p-6">
        <h1 className="text-3xl font-bold text-gray-900">
          {clinicName ? `${clinicName} Dashboard` : 'Dashboard'}
        </h1>
        <p className="text-gray-600 mt-2">
          Overview of clinic performance and financial metrics
        </p>
      </div>

      {/* Income Report Section */}
      <IncomeReport />

      {/* Future sections can be added here */}
      {/* <OtherDashboardComponents /> */}
    </div>
  );
}

export default Dashboard;
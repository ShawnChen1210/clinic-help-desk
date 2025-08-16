
import React, { useEffect } from 'react';
import { Outlet, useParams } from 'react-router-dom';
import { useClinic } from "../../context/ClinicContext";
import Navbar from "../molecules/Navbar";

export default function Layout() {
  const { clinic_id } = useParams();
  const { loadClinicData, clinicName, loading } = useClinic();

  useEffect(() => {
    if (clinic_id) {
      loadClinicData(clinic_id);
    }
  }, [clinic_id]);

  // Show loading state while clinic data is being fetched
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading clinic data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-[12rem,1fr]">
      <Navbar />
      <main className="flex-grow p-4 sm:p-8 bg-gray-100 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
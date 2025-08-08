import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from "../molecules/Navbar";

export default function Layout() {
  return (
    <div className="grid grid-cols-[12rem,1fr]">
      <Navbar />
      <main className="flex-grow p-4 sm:p-8 bg-gray-100 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
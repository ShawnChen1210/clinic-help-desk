// Updated App.js
import React, { useState, useEffect } from 'react';
import {BrowserRouter, Routes, Route, Navigate} from 'react-router-dom';
import SpreadSheet from './pages/Spreadsheet'
import Dashboard from './pages/Dashboard';
import UploadFile from './pages/UploadFiles';
import Analytics from "./pages/Analytics";
import {AppProviders} from "./context";
import Members from "./pages/Members";
import Payroll from "./pages/Payroll";
import Layout from "./components/organisms/Layout";
import ExternalRedirect from "./components/atoms/ExternalRedirect";
import Clinics from "./pages/Clinics";

function App() {
  return (
    <AppProviders>
      <BrowserRouter>
        <Routes>
          <Route path='/chd-app'>
            <Route index element={<Navigate to="clinics" replace />} />
            <Route path="clinics" element={<Clinics/>}/>
            <Route path=":clinic_id" element={<Layout/>}>
              <Route index element={<Dashboard/>}/>
              <Route path="spreadsheet/:sheet_id" element={<SpreadSheet />}/> {/* Remove leading slash */}
              <Route path="upload" element={<UploadFile />}/>
              <Route path="members" element={<Members />} />
              <Route path="payroll/:userId" element={<Payroll />} />
            </Route>
          </Route>
          <Route path="/" element={<ExternalRedirect to="/" />} />
        </Routes>
      </BrowserRouter>
    </AppProviders>
  )
}

export default App;
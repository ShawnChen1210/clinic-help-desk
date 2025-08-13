// Updated App.js
import React, { useState, useEffect } from 'react';
import {BrowserRouter, Routes, Route, Navigate} from 'react-router-dom';
import SpreadSheet from './pages/Spreadsheet'
import Dashboard from './pages/Dashboard';
import UploadFile from './pages/UploadFiles';
import Analytics from "./pages/Analytics";
import Members from "./pages/Members";
import Layout from "./components/organisms/Layout";
import ExternalRedirect from "./components/atoms/ExternalRedirect";

function App() {
  return (
      <BrowserRouter>
          <Routes>
              {/*Everything spreadsheet related will have a vertical nav bar and have its own layout in Layout.js*/}
              <Route path="/spreadsheet/:sheet_id" element={<Layout/>}>
                  <Route index element={<SpreadSheet />}/>
                  <Route path="upload" element={<UploadFile />}/>
                  <Route path="members" element={<Members />} />
              </Route>
              <Route path="/" element={<ExternalRedirect to="/dashboard/" />} />
          </Routes>
      </BrowserRouter>
  )
}

export default App;
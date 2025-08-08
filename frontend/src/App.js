import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SpreadSheet from './pages/Spreadsheet'
import Dashboard from './pages/Dashboard';
import UploadFile from './pages/UploadFiles';
import Analytics from "./pages/Analytics";
import Layout from "./components/organisms/Layout";

function App() {
  return (
      <BrowserRouter>
          <Routes>
              {/*Everything spreadsheet related will have a vertical nav bar and have its own layout in Layout.js*/}
              <Route path="/spreadsheet/:sheet_id" element={<Layout/>}>
                  <Route index element={<SpreadSheet />}/>
                  <Route path="upload" element={<UploadFile />}/>
                  <Route path="analytics" element={<Analytics/>} />
              </Route>
              <Route path="/dashboard" element={<Dashboard />} /> {/*IN CASE OF ROUTING MISTAKE*/}
              <Route path="/" element={<Dashboard />} />
          </Routes>
      </BrowserRouter>
  )
}

export default App;

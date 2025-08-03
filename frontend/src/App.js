import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SpreadSheet from './pages/Spreadsheet'
import Dashboard from './pages/Dashboard';
import UploadFile from './pages/UploadFiles';
import axios from 'axios';

function App() {
  return (
      <BrowserRouter>
          <Routes>
              <Route path="/spreadsheet/:sheet_id" element={<SpreadSheet />}/>
              <Route path="/spreadsheet/:sheet_id/upload" element={<UploadFile />}/>
              <Route path="/dashboard" element={<Dashboard />} /> {/*IN CASE OF ROUTING MISTAKE*/}
              <Route path="/" element={<Dashboard />} />
          </Routes>
      </BrowserRouter>
  )
}

export default App;

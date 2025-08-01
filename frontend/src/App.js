import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SpreadSheet from './pages/spreadsheet'
import axios from 'axios';

function App() {
  return (
      <BrowserRouter>
          <Routes>
              <Route path="/spreadsheet/:sheet_id" element={<SpreadSheet />}/>
          </Routes>
      </BrowserRouter>
  )
}

export default App;

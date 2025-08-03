import React from 'react';
import { Link } from 'react-router-dom';

//THIS IS JUST IN CASE THERE IS A ROUTING MISTAKE WITH THE DASHBOARD
function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the main page.</p>
      {/* Add a link to a test spreadsheet page */}
      <Link to="/spreadsheet/1a3HLCoCav5swZ2rBwNcMe8DMrL2FyD-ZPdnWdEfrYbg">
        Go to Test Spreadsheet
      </Link>
    </div>
  );
}

export default Dashboard;
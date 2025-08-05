import React from 'react';
import { Link } from 'react-router-dom';

//THIS PAGE IS JUST IN CASE THERE IS A ROUTING MISTAKE WITH THE DASHBOARD
function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
      <p>Welcome to the dashboard.</p>
      {/* Add a link to a test spreadsheet page */}
      <Link to="/dashboard">
        Go to Dashboard
      </Link>
    </div>
  );
}

export default Dashboard;
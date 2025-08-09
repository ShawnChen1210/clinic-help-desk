import React, {use} from 'react';
import { NavLink, useParams } from 'react-router-dom';

export default function Navbar() {
    const {sheet_id} = useParams()
  // This function is used by NavLink to apply a style to the active link
  const navLinkStyles = ({ isActive }) => {
    return {
      fontWeight: isActive ? 'bold' : 'normal',
      backgroundColor: isActive ? 'rgba(75, 85, 99, 1)' : '', // gray-600
    };
  };

  return (
      <div className="sticky top-0 h-screen w-48 bg-gray-800 text-white flex flex-col">
          <div className="p-4 border-b border-gray-700 text-2xl font-bold">
              <NavLink to={'/'}>
                  Clinic Help Desk
              </NavLink>
          </div>
          <nav className="flex-grow p-4">
              <NavLink to={`/spreadsheet/${sheet_id}`} style={navLinkStyles}
                       className="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700" end>
                  Spreadsheet
              </NavLink>
              <NavLink to={`/spreadsheet/${sheet_id}/analytics`} style={navLinkStyles}
                       className="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700">
                  Analytics
              </NavLink>
              {/* Add more links here */}
          </nav>
      </div>
  );
}
import React, { useState, useEffect } from 'react';
import { NavLink, useParams } from 'react-router-dom';
import api from '../../utils/axiosConfig';

export default function Navbar() {
    const { sheet_id } = useParams();
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        fetchCurrentUser();
    }, []);

    const fetchCurrentUser = async () => {
        try {
            const response = await api.get('/api/members/current-user/');
            setCurrentUser(response.data);
            console.log(currentUser);
        } catch (error) {
            console.error('Error fetching current user:', error);
        }
    };

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

                {/* Only show Members link to staff and superusers */}
                {currentUser && (currentUser.is_staff || currentUser.is_superuser) && (
                    <NavLink to={`/spreadsheet/${sheet_id}/members`} style={navLinkStyles}
                             className="block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700">
                        Members
                    </NavLink>
                )}
            </nav>
        </div>
    );
}
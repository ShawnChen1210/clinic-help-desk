import React, { useState, useEffect } from 'react';
import { NavLink, useParams } from 'react-router-dom';
import { useClinic } from "../../context/ClinicContext";
import api from '../../utils/axiosConfig';

export default function Navbar() {
    const { clinic_id } = useParams();
    const { clinicName, sheets, loading: clinicLoading } = useClinic();
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        fetchCurrentUser();
    }, []);

    const fetchCurrentUser = async () => {
        try {
            const response = await api.get('/api/members/current-user/');
            setCurrentUser(response.data);
        } catch (error) {
            console.error('Error fetching current user:', error);
        }
    };

    // Get the default sheet (compensation & sales) for direct access
    const defaultSheetId = sheets?.compensation_sales_sheet_id;

    // This function is used by NavLink to apply a style to the active link
    const navLinkStyles = ({ isActive }) => {
        return isActive ? 'bg-gray-600 font-bold' : '';
    };

    return (
        <div className="sticky top-0 h-screen w-48 bg-gray-800 text-white flex flex-col">
            <div className="p-4 border-b border-gray-700">
                <NavLink to={'/'} className="text-xl font-bold hover:text-gray-300">
                    Clinic Help Desk
                </NavLink>
                {clinicName && (
                    <div className="text-sm text-gray-400 mt-1">
                        {clinicName}
                    </div>
                )}
            </div>

            <nav className="flex-grow p-4 space-y-2">
                {/* Dashboard Link */}
                {clinic_id && (
                    <NavLink
                        to={`/chd-app/${clinic_id}`}
                        className={({ isActive }) =>
                            `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                        }
                        end
                    >
                        Dashboard
                    </NavLink>
                )}

                {/* Spreadsheets Link - Goes to default (compensation & sales) */}
                {currentUser && (currentUser.is_staff || currentUser.is_superuser) && clinic_id && (
                    <>
                        {defaultSheetId ? (
                            <NavLink
                                to={`/chd-app/${clinic_id}/spreadsheet/${defaultSheetId}`}
                                className={({ isActive }) =>
                                    `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                                }
                            >
                                Spreadsheets
                            </NavLink>
                        ) : clinicLoading ? (
                            <div className="py-2 px-4 text-gray-400 text-sm">
                                Loading sheets...
                            </div>
                        ) : (
                            <div className="py-2 px-4 text-gray-400 text-sm">
                                No sheets available
                            </div>
                        )}
                    </>
                )}

                {/* Upload File Link */}
                {currentUser && (currentUser.is_staff || currentUser.is_superuser) && clinic_id && (
                    <NavLink
                        to={`/chd-app/${clinic_id}/upload`}
                        className={({ isActive }) =>
                            `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                        }
                    >
                        Upload File
                    </NavLink>
                )}

                {/* Members Link - Only show to staff and superusers */}
                {currentUser && (currentUser.is_staff || currentUser.is_superuser) && clinic_id && (
                    <NavLink
                        to={`/chd-app/${clinic_id}/members`}
                        className={({ isActive }) =>
                            `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                        }
                    >
                        Members
                    </NavLink>
                )}

                {/* Show message if no clinic is selected */}
                {!clinic_id && (
                    <div className="py-4 px-4 text-gray-400 text-sm text-center">
                        Select a clinic to view options
                    </div>
                )}
            </nav>

            {/* User Info at Bottom */}
            {currentUser && (
                <div className="p-4 border-t border-gray-700">
                    <div className="text-sm">
                        <div className="font-medium">{currentUser.username}</div>
                        <div className="text-gray-400">
                            {currentUser.is_superuser ? 'Super Admin' :
                             currentUser.is_staff ? 'Staff' : 'User'}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
import React, { useState, useEffect } from 'react';
import { NavLink, useParams, useLocation } from 'react-router-dom';
import { useClinic } from "../../context/ClinicContext";
import api from '../../utils/axiosConfig';

export default function Navbar() {
    const { clinic_id } = useParams();
    const location = useLocation();
    const { clinicName, sheets, loading: clinicLoading } = useClinic();
    const [currentUser, setCurrentUser] = useState(null);

    useEffect(() => {
        fetchCurrentUser();
    }, []);

    // Clean up temp files when leaving upload pages
    useEffect(() => {
        if (!location.pathname.includes('/upload')) {
            api.post('/api/spreadsheets/cleanup_temp_files/').catch(() => {});
        }
    }, [location.pathname]);

    const fetchCurrentUser = async () => {
        try {
            const response = await api.get('/api/members/current-user/');
            setCurrentUser(response.data);
        } catch (error) {
            console.error('Error fetching current user:', error);
        }
    };

    const defaultSheetId = sheets?.compensation_sales_sheet_id;
    const navLinkStyles = ({ isActive }) => isActive ? 'bg-gray-600 font-bold' : '';

    return (
        <div className="sticky top-0 h-screen w-48 bg-gray-800 text-white flex flex-col">
            <div className="p-4 border-b border-gray-700">
                <NavLink to={'/'} className="text-xl font-bold hover:text-gray-300">
                    Clinic Help Desk
                </NavLink>
                {clinicName && (
                    <div className="text-sm text-gray-400 mt-1">{clinicName}</div>
                )}
            </div>

            <nav className="flex-grow p-4 space-y-2">
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

                {currentUser?.is_staff && clinic_id && (
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
                            <div className="py-2 px-4 text-gray-400 text-sm">Loading sheets...</div>
                        ) : (
                            <div className="py-2 px-4 text-gray-400 text-sm">No sheets available</div>
                        )}

                        <NavLink
                            to={`/chd-app/${clinic_id}/upload`}
                            className={({ isActive }) =>
                                `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                            }
                        >
                            Upload File
                        </NavLink>

                        <NavLink
                            to={`/chd-app/${clinic_id}/members`}
                            className={({ isActive }) =>
                                `block py-2.5 px-4 rounded transition duration-200 hover:bg-gray-700 ${navLinkStyles({ isActive })}`
                            }
                        >
                            Members
                        </NavLink>
                    </>
                )}

                {!clinic_id && (
                    <div className="py-4 px-4 text-gray-400 text-sm text-center">
                        Select a clinic to view options
                    </div>
                )}
            </nav>

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
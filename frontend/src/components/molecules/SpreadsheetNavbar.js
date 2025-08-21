import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useClinic } from "../../context/ClinicContext";
import LinkButton from "../atoms/LinkButton";

const SpreadsheetNavbar = ({ userData, sheetData }) => {
    const { clinic_id, sheet_id } = useParams();
    const navigate = useNavigate();
    const { getAvailableSheets, getSheetInfo } = useClinic();

    const availableSheets = getAvailableSheets();
    const currentSheetInfo = getSheetInfo(sheet_id);

    const handleSheetChange = (newSheetId) => {
        if (newSheetId !== sheet_id) {
            navigate(`/chd-app/${clinic_id}/spreadsheet/${newSheetId}`);
        }
    };

    const getSheetDisplayName = (sheet) => {
        const typeLabels = {
            'compensation_sales': 'Compensation + Sales',
            'daily_transaction': 'Daily Transaction',
            'transaction_report': 'Transaction Report',
            'payment_transaction': 'Payment Transaction',
            'time_hour': 'Hours Report'  // Added 5th sheet type
        };
        return typeLabels[sheet.type] || sheet.label;
    };

    return (
        <div className="flex flex-wrap justify-between items-center bg-white p-4 sm:p-6 rounded-lg shadow-md mb-8">
            <div className="flex-1 min-w-0">
                <h1 className="text-xl sm:text-2xl font-bold text-gray-800">
                    Welcome, {userData?.username}!
                </h1>
                <h4 className="text-sm font-medium text-gray-500 mt-1">
                    Sheet: {sheetData?.sheet_name || 'Loading...'}
                </h4>
                {currentSheetInfo && (
                    <p className="text-xs text-gray-400 mt-1">
                        Type: {currentSheetInfo.label}
                    </p>
                )}
            </div>

            {/* Sheet Navigation Dropdown */}
            <div className="flex items-center space-x-2 mt-4 sm:mt-0">
                <div className="relative">
                    <select
                        value={sheet_id}
                        onChange={(e) => handleSheetChange(e.target.value)}
                        className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 pr-8 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 transition-colors cursor-pointer appearance-none"
                    >
                        {availableSheets.map((sheet) => (
                            <option
                                key={sheet.googleSheetId}
                                value={sheet.googleSheetId}
                                className="bg-white text-black"
                            >
                                {getSheetDisplayName(sheet)}
                            </option>
                        ))}
                    </select>
                    <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                        <svg className="h-4 w-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </div>
                </div>

                {/* Action Buttons */}
                <LinkButton
                    text="Upload CSV"
                    link={`/chd-app/${clinic_id}/spreadsheet/${sheet_id}/upload`}
                />
                <LinkButton
                    text="Open In Google Sheets"
                    link={`https://docs.google.com/spreadsheets/d/${sheet_id}`}
                    newTab={true}
                />
            </div>
        </div>
    );
};

export default SpreadsheetNavbar;
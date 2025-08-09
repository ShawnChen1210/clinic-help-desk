import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import api from "../../utils/axiosConfig";
import ColumnSelector from "../atoms/ColumnSelector";
import BarChartDisplay from "../atoms/BarChart"; // Import the new chart component

export default function IncomeBarChart({ headers }) {
    const [incomeColumns, setIncomeColumns] = useState([]);
    const [dateColumn, setDateColumn] = useState(null);
    const [reportData, setReportData] = useState(null);
    const [loading, setLoading] = useState(true);
    const { sheet_id } = useParams();

    // On load, try to fetch saved preferences.
    useEffect(() => {
        const fetchPreferences = async () => {
            try {
                // This endpoint should be GET /api/sheet-preferences/{sheet_id}/
                const res = await api.get(`/api/sheet-preferences/${sheet_id}/`);
                setIncomeColumns(res.data.income_columns);
                setDateColumn(res.data.date_column);
                // If preferences are found, immediately generate the report
                await handleSubmit(res.data.date_column, res.data.income_columns);
            } catch (error) {
                if (error.response?.status === 404) {
                    console.log("No preferences found, user needs to select columns.");
                } else {
                    console.error('Failed to fetch preferences', error);
                }
            } finally {
                setLoading(false);
            }
        };
        fetchPreferences();
    }, [sheet_id]);

    // This function handles both generating the report and saving preferences
    const handleSubmit = async (selectedDate, selectedIncomes) => {

        setLoading(true);
        try {
            // 1. Generate the report
            const reportRes = await api.post(`/api/analytics/${sheet_id}/income_summary/`, {
                date_column: selectedDate,
                income_columns: selectedIncomes,
            });
            setReportData(reportRes.data);

            // 2. Save the preferences for next time (fire and forget)
            // This endpoint should be POST /api/sheet-preferences/
            api.post(`/api/sheet-preferences/`, {
                sheet_id: sheet_id,
                date_column: selectedDate,
                income_columns: selectedIncomes,
            }).catch(err => console.error("Could not save preferences:", err));

        } catch (error) {
            console.error('Failed to generate report:', error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="text-center p-8">Loading...</div>;
    }

    // If we have report data, show the chart. Otherwise, show the selection form.
    return (
        <div>
            {reportData ? (
                <BarChartDisplay reportData={reportData} />
            ) : (
                <div className="p-8 bg-white rounded-lg shadow-md">
                    <div>
                        <h3 className="font-bold text-lg mb-2">Select the Date Column</h3>
                        <ColumnSelector headers={headers} selected={dateColumn} onSelect={setDateColumn} selectionMode="single" />
                    </div>
                    <div className="mt-6">
                        <h3 className="font-bold text-lg mb-2">Select the Income Column(s)</h3>
                        <ColumnSelector headers={headers} selected={incomeColumns} onSelect={setIncomeColumns} selectionMode="multiple" />
                    </div>
                    <div className="mt-8 text-center">
                        <button
                            onClick={() => handleSubmit(dateColumn, incomeColumns)}
                            className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-6 rounded-lg"
                        >
                            Generate Report
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
import { useEffect, useMemo, useState } from 'react';
import { Chart } from 'react-charts'
import api from "../utils/axiosConfig";
import {useParams} from "react-router-dom";
import IncomeBarChart from "../components/organisms/IncomeBarChart";

export default function Analytics() {
    const [headers, setHeaders] = useState(null)
    const { sheet_id } = useParams()

    useEffect(() => {

        const onLoad = async () => {
            try {
                const res = await api.get(`api/analytics/${sheet_id}/get_sheet_headers/`)
                if (res.data.columns) {
                    setHeaders(res.data.columns)
                }
            } catch (error) {
                console.error('Failed to fetch headers', error.response.data.error);
            }
        }

        onLoad()
    }, [])


    if (!headers) {
        return (
            <div
                className="flex flex-col items-center justify-center p-8 bg-yellow-50 border-l-4 border-yellow-400 rounded-lg shadow-md">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 text-yellow-500" fill="none"
                     viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <h3 className="mt-4 text-xl font-bold text-yellow-800">No Data Available</h3>
                <p className="mt-1 text-center text-yellow-700">
                    Please upload a CSV file to this spreadsheet to view the analytics chart.
                </p>
            </div>
        );
    }


    return (
        <div>
            <IncomeBarChart headers={headers}/>
        </div>
    );
}
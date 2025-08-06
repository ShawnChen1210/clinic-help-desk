import React, {useState} from "react";
import {useParams} from "react-router-dom";
import api from '../../utils/axiosConfig'
import SelectableTable from "./SelectableTable";

export default function JoinTableForm({tableL, tableR, onJoinSuccess}) {
    const [selectionLeft, setSelectionLeft] = useState(null); //for current spreadsheet
    const [selectionRight, setSelectionRight] = useState(null); //for uploaded spreadsheet
    const { sheet_id } = useParams()

    const handleSubmit = async () => {
        if (!selectionLeft || !selectionRight) {
            alert('Please select a column from each table.');
            return;
        }

        console.log('Submitting selections to backend:', {
          csvColumn: selectionLeft,
          googleSheetColumn: selectionRight,
        })

        try {
            const response = await api.post(
                `api/spreadsheets/${sheet_id}/merge_sheets/`,
                {
                    left_column: selectionLeft,
                    right_column: selectionRight
                }
            )

            onJoinSuccess(response.data)
            alert('Merge successful!');
        } catch (error) {
            console.error('Merge failed:', error.response.data.error);
            alert('Merge failed.');
        }
    }

    return (
        <div>

            {/* Container for side-by-side tables */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <SelectableTable
                    title="Current Spreadsheet"
                    table={tableL}
                    selectedColumn={selectionLeft}
                    onColumnSelect={setSelectionLeft} // Pass the state setter function
                />
                <SelectableTable
                    title="Uploaded Spreadsheet"
                    table={tableR}
                    selectedColumn={selectionRight}
                    onColumnSelect={setSelectionRight} // Pass the state setter function
                />
            </div>

            <div className="mt-8 text-center">
                <button
                    onClick={handleSubmit}
                    className="bg-green-500 hover:bg-green-600 text-white font-bold py-3 px-8 rounded-lg transition-colors disabled:bg-gray-400"
                    disabled={!selectionLeft || !selectionRight} // Button is disabled until both are selected
                >
                    Submit Merge
                </button>
            </div>
        </div>
    );
}
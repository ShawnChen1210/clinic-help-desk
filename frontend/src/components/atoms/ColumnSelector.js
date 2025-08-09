import React from 'react';

export default function ColumnSelector({ headers, selected, onSelect, selectionMode = 'single' }) {

  const handleSelect = (header) => {
    if (selectionMode === 'multiple') {
      // For multi-select, treat 'selected' as an array
      const currentSelection = selected || [];
      if (currentSelection.includes(header)) {
        // If already selected, remove it from the array
        onSelect(currentSelection.filter(item => item !== header));
      } else {
        // If not selected, add it to the array
        onSelect([...currentSelection, header]);
      }
    } else {
      // For single-select, check if we're deselecting
      if (selected === header) {
        onSelect(null); // Deselect if clicked again
      } else {
        onSelect(header); // Select the new item
      }
    }
  };

  return (
    <div className="flex flex-wrap gap-2 p-4 border rounded-lg bg-gray-50">
      {headers.map(header => {
        // Check if the current header is selected based on the mode
        const isSelected = selectionMode === 'multiple'
          ? selected?.includes(header)
          : selected === header;

        return (
          <button
            key={header}
            onClick={() => handleSelect(header)}
            className={`
              py-2 px-4 rounded-full border text-sm font-semibold transition-colors
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-400
              ${isSelected
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
              }
            `}
          >
            {header}
          </button>
        );
      })}
    </div>
  );
}
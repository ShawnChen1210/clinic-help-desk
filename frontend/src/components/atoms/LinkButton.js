import React from "react";
import { Link } from 'react-router-dom';

export default function LinkButton({ text, link }) {
    return (
        <div className="flex space-x-2 mt-4 sm:mt-0">
            <Link to={link}>
                <button className="bg-gray-600 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded-lg">
                    {text}
                </button>
            </Link>
        </div>
    );
}

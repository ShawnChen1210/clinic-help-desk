import { useEffect, useState } from 'react';
import { fetchUser } from '../services/auth';
import { useParams } from 'react-router-dom';

export default function Spreadsheet() {
  const [userData, setUserData] = useState(null);
  const { sheetId } = useParams() //gets sheet id

  useEffect(() => {
    fetchUser().then(res => setUserData(res.data));
  }, []);

  return (
    <div>
      <h1>Welcome, {userData?.username}!</h1>
      <h1>sheet id: {sheetId}</h1>
    </div>
  );
}
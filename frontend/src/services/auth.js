//Centralize API calls to Django
import axios from '../utils/axiosConfig';

export const login = (username, password) => {
  return axios.post('/accounts/login/', { username, password });  // Django's login URL
};

export const fetchUser = () => {
  return axios.get('/api/user/');
};
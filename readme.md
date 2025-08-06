WELCOME TO CLINIC HELP DESK!
-
Overall Project Architecture:
-
- The project is built with Django and React
- A method of React serving static files to the client is used for the django-react integration, meaning no seperate server for the frontend, everything runs from one server. To this end, every time a change is made in the /frontend/, in the terminal cd to frontend and run "npm run build" to build and register your changes so it can be seen in the django development server.
- User authentication is done with django's built in authentication
- Everything spreadsheet related is coded in react

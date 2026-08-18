// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyDRaHzqj1MmwWnbP3KTFDb93YNVPkjqWU0",
  authDomain: "clubs-f66f8.firebaseapp.com",
  databaseURL: "https://clubs-f66f8-default-rtdb.firebaseio.com",
  projectId: "clubs-f66f8",
  storageBucket: "clubs-f66f8.firebasestorage.app",
  messagingSenderId: "458953822512",
  appId: "1:458953822512:web:a6cd1919fe24854325f8f5",
  measurementId: "G-7VQZC0HFDL"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
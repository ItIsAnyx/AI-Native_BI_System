import { Outlet } from "react-router";

import Footer from "../components/common/Footer";
import Header from "../components/common/Header";

export default function MainLayout() {
    return (
        <>
            <Header/>

            <Outlet/>

            <Footer/>
        </>
    );
}

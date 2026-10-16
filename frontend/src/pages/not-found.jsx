import { NavLink } from "react-router";
import Button from "../components/ui/Button";

export default function NotFound() {

    return (
        <main>
            <div>

                <div>
                    <span>
                        404
                    </span>
                </div>

                <h2>
                    Страница не найдена
                </h2>

                <p>
                    К сожалению, такой страницы не существует.
                    Возможно, она была удалена, перемещена
                    или вы ошиблись в адресе.
                </p>

                <div>
                    <NavLink to="/">
                        <Button>
                            На главную
                        </Button>
                    </NavLink>
                </div>

                <p>
                    Ошибка 404 · Страница не существует
                </p>
            </div>
        </main>
    );
}

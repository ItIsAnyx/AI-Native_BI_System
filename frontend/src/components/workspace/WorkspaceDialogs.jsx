import CreateProjectDialog from "./dialogs/CreateProjectDialog";
import DeleteChatDialog from "./dialogs/DeleteChatDialog";
import DeleteProjectDialog from "./dialogs/DeleteProjectDialog";
import MoveChatDialog from "./dialogs/MoveChatDialog";

export default function WorkspaceDialogs({
  modal,
  workspace,
  onClose,
  onDialog,
  notify,
  onProjectCreated,
}) {
  const shared = { workspace, onClose, notify };
  const chat = workspace.chats.find((item) => item.id === modal.id);
  const project = workspace.projects.find((item) => item.id === modal.id);

  switch (modal.type) {
    case "create-project":
      return (
        <CreateProjectDialog
          {...shared}
          modal={modal}
          onProjectCreated={onProjectCreated}
        />
      );
    case "delete-chat":
      return chat ? <DeleteChatDialog {...shared} chat={chat} /> : null;
    case "delete-project":
      return project ? (
        <DeleteProjectDialog {...shared} project={project} />
      ) : null;
    case "move":
      return chat ? (
        <MoveChatDialog {...shared} chat={chat} onDialog={onDialog} />
      ) : null;
    default:
      return null;
  }
}

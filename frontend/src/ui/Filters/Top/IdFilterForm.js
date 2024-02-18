export default function Component() {
  return (
    <form className="grid grid-flow-col auto-cols-max justify-end">
      <span className="m-auto">from</span>
      <input
        type="text"
        name="id_from"
        id="id-from"
        placeholder="####"
        className="input-base mx-3 w-14.4 ps-3 p-2.5"
      />
      <span className="m-auto">to</span>
      <input
        type="text"
        name="id_to"
        id="id-to"
        placeholder="####"
        className="input-base ml-3 w-14.4 ps-3 p-2.5"
      />
    </form>
  );
}
